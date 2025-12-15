# api/index.py
import os
import time
from fastapi import FastAPI, HTTPException, Security
from fastapi.security.api_key import APIKeyQuery
from scraper.fetcher import ScoreFetcher
from vercel_kv import kv
import json

app = FastAPI()

# 定义API密钥认证方式，从查询参数 `secret` 中获取
api_key_query = APIKeyQuery(name="secret", auto_error=False)

def get_api_key(api_key: str = Security(api_key_query)):
    """校验API密钥"""
    expected_api_key = os.environ.get("API_SECRET_TOKEN")
    if not expected_api_key:
        raise HTTPException(status_code=500, detail="服务器未配置API密钥")
    if api_key == expected_api_key:
        return api_key
    else:
        raise HTTPException(status_code=403, detail="提供的密钥无效或缺失")

@app.post("/api/fetch-scores")
async def trigger_fetch_scores(api_key: str = Security(get_api_key)):
    """
    触发成绩获取和存储任务。
    需要提供正确的 `secret` 查询参数进行认证。
    """
    username = os.environ.get("SWJTU_USERNAME")
    password = os.environ.get("SWJTU_PASSWORD")

    if not username or not password:
        raise HTTPException(status_code=500, detail="服务器未配置学号或密码环境变量")

    print("--- 任务开始: 准备获取成绩 ---")
    fetcher = ScoreFetcher(username=username, password=password)

    try:
        # 1. 登录
        login_success = fetcher.login()
        if not login_success:
            return {"status": "error", "message": "登录失败，请检查Vercel日志。"}

        # 2. 获取全部成绩
        all_scores = fetcher.get_all_scores()
        if all_scores:
            # 存储到 Vercel KV，使用 json.dumps 转换为字符串
            # 键名可以加上用户名以作区分（如果未来支持多用户）
            kv.set(f"all_scores_{username}", json.dumps(all_scores, ensure_ascii=False))
            print(f"已将 {len(all_scores)} 条总成绩记录存入 Vercel KV。")
        else:
            print("未获取到总成绩数据。")

        # 延迟一下，模拟人类行为
        time.sleep(2)

        # 3. 获取平时成绩
        normal_scores = fetcher.get_normal_scores()
        if normal_scores:
            kv.set(f"normal_scores_{username}", json.dumps(normal_scores, ensure_ascii=False))
            print(f"已将 {len(normal_scores)} 门课程的平时成绩存入 Vercel KV。")
        else:
            print("未获取到平时成绩数据。")
            
        print("--- 任务完成 ---")
        return {
            "status": "success",
            "message": "成绩获取和存储任务已完成。",
            "summary": {
                "all_scores_count": len(all_scores) if all_scores else 0,
                "normal_scores_count": len(normal_scores) if normal_scores else 0
            }
        }

    except Exception as e:
        print(f"执行任务时发生严重错误: {e}")
        raise HTTPException(status_code=500, detail=f"执行爬虫任务时发生内部错误: {str(e)}")

# 你可以添加一个根路径的端点，以便检查服务是否在线
@app.get("/")
def read_root():
    return {"status": "online", "message": "SWJTU Score Fetcher API is running."}