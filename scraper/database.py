
# scraper/database.py
import os
import psycopg2
import json
from psycopg2.extras import execute_batch

# 从环境变量获取数据库连接URL
DATABASE_URL = os.environ.get('POSTGRES_URL')

def get_db_connection():
    """建立并返回一个数据库连接"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        raise

def init_db():
    """
    初始化数据库，创建 scores 表 (如果不存在)。
    这个函数可以安全地多次运行。
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS scores (
                    academic_year VARCHAR(20) NOT NULL,
                    semester VARCHAR(5) NOT NULL,
                    course_code VARCHAR(50) NOT NULL,
                    course_name VARCHAR(255),
                    score VARCHAR(50),
                    credits NUMERIC(4, 1),
                    course_nature VARCHAR(100),
                    teacher VARCHAR(255),
                    final_score VARCHAR(50),
                    normal_score VARCHAR(50),
                    exam_type VARCHAR(100),
                    remarks TEXT,
                    normal_scores_details JSONB, -- 存储平时成绩明细
                    last_updated_at TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY (academic_year, semester, course_code)
                );
            """)
            conn.commit()
            print("Database table 'scores' initialized successfully.")
    finally:
        conn.close()

def upsert_scores(scores_data):
    """
    使用 UPSERT 逻辑将成绩数据批量插入或更新到数据库。
    返回新增和更新的记录数量。
    """
    conn = get_db_connection()
    inserted_count = 0
    updated_count = 0
    
    # 准备用于批量操作的数据元组列表
    data_to_upsert = [
        (
            s.get('学年'), s.get('学期'), s.get('代码'), s.get('课程名称'),
            s.get('成绩'), s.get('学分'), s.get('性质'), s.get('教师'),
            s.get('期末'), s.get('平时'), s.get('类型'), s.get('备注'),
            json.dumps(s.get('normal_details')) if s.get('normal_details') else None # 转换list为JSON字符串
        ) for s in scores_data
    ]

    # ON CONFLICT 语句是这里的核心魔法
    # 它告诉 Postgres：当插入的行与现有的行在主键上冲突时，执行 UPDATE 操作
    # EXCLUDED.* 指的是你试图插入的新行的数据
    upsert_sql = """
        INSERT INTO scores (
            academic_year, semester, course_code, course_name, score, credits,
            course_nature, teacher, final_score, normal_score, exam_type, remarks,
            normal_scores_details, last_updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (academic_year, semester, course_code) DO UPDATE SET
            course_name = EXCLUDED.course_name,
            score = EXCLUDED.score,
            credits = EXCLUDED.credits,
            course_nature = EXCLUDED.course_nature,
            teacher = EXCLUDED.teacher,
            final_score = EXCLUDED.final_score,
            normal_score = EXCLUDED.normal_score,
            exam_type = EXCLUDED.exam_type,
            remarks = EXCLUDED.remarks,
            normal_scores_details = EXCLUDED.normal_scores_details,
            last_updated_at = NOW()
        RETURNING xmax; -- xmax=0表示INSERT, 非0表示UPDATE
    """
    
    try:
        with conn.cursor() as cur:
            # 使用 execute_batch 会更高效，但为了获取每行的返回状态，我们使用循环
            for record in data_to_upsert:
                cur.execute(upsert_sql, record)
                result = cur.fetchone()[0]
                if result == 0:
                    inserted_count += 1
                else:
                    updated_count += 1
            conn.commit()
            print(f"Upsert complete. Inserted: {inserted_count}, Updated: {updated_count}")
    finally:
        conn.close()
        
    return {"inserted": inserted_count, "updated": updated_count}