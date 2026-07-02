import time
from datetime import datetime
import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from core.agent import AutonomousManagerAgent
from tools.mail_tools import has_new_unread_emails

scheduler = BlockingScheduler(timezone="Asia/Seoul")
agent = AutonomousManagerAgent()

def get_now_kst() -> datetime:
    return datetime.now(pytz.timezone("Asia/Seoul"))

def job_morning_briefing():
    if get_now_kst().weekday() in [5, 6]: return
    print("[Worker] 실행: 자율 아침 보고")
    prompt = "지금은 아침 출근 시간입니다. 1. 읽지 않은 메일을 확인하고 필요한 조치를 취하세요. 2. 오늘 일정을 확인하세요. 3. 미완료된 할 일을 확인하세요. 4. 밤사이 증시(KOSPI, KOSDAQ, S&P 500, 나스닥, 환율)와 기술 트렌드 뉴스를 검색하여 브리핑해주세요. 이를 종합하여 최종 아침 보고서를 작성하세요."
    try:
        report = agent.run_task(prompt)
        agent.send_webhook(report)
    except Exception as e:
        print(f"[Worker] 아침 보고 실패: {e}")

def job_evening_briefing():
    if get_now_kst().weekday() in [5, 6]: return
    print("[Worker] 실행: 자율 저녁 보고")
    prompt = "지금은 퇴근 시간입니다. 1. 읽지 않은 메일을 확인하고 초안을 작성하세요. 2. 내일 일정을 확인하세요. 3. 미완료된 할 일들을 점검하세요. 저녁 시간이므로 새로운 할 일을 등록하지 마세요. 오늘 하루 성과와 내일의 준비에 초점을 맞춰 최종 저녁 보고서를 작성하세요."
    try:
        report = agent.run_task(prompt)
        agent.send_webhook(report)
    except Exception as e:
        print(f"[Worker] 저녁 보고 실패: {e}")

def job_check_deadlines():
    if get_now_kst().weekday() in [5, 6]: return
    print("[Worker] 실행: 할 일 마감 시간 점검")
    try:
        status = agent.tasks_agent.check_deadlines_and_notify()
        print(f"[Worker] 할 일 마감 점검 완료: {status}")
    except Exception as e:
        print(f"[Worker] 할 일 마감 점검 실패: {e}")

def job_autonomous_monitoring():
    if get_now_kst().weekday() in [5, 6]: return
    print("[Worker] 실행: 자율 실시간 메일 모니터링 (2분 주기)")
    try:
        # Zero-LLM Pre-filtering Check
        if not has_new_unread_emails():
            print("[Worker] [Scheduler] 신규 읽지 않은 메일이 없습니다. (LLM 스킵)")
            return
            
        prompt = "이메일을 확인하여 우주현 책임에게 전달된 신규 업무 조치/협조/확인 요청 건이 있는지 검사하고, 발견 시 오늘 18:00~19:00 구글 캘린더 일정 및 Google Tasks 할 일 목록에 각각 즉시 자동 등록하세요."
        report = agent.run_task(prompt)
        
        # If a task request was detected and handled, send a real-time Google Chat alert
        if "[업무요청 감지]" in report:
            print("[Worker] [Scheduler] 실시간 신규 업무 조치가 완료되어 구글 챗에 실시간 보고를 전송합니다.")
            lines = report.split("\n")
            extracted = []
            for line in lines:
                if "핵심요청:" in line:
                    extracted.append(line.split("핵심요청:")[1].strip())
            
            if extracted:
                req_summary = "\n".join([f"- {r}" for r in extracted])
                notification = f"💬 *[자율 비서 실시간 조치 알림]* 💬\n\n읽지 않은 신규 이메일에서 업무 협조/조치 요청을 감지하여 캘린더 및 할 일 목록에 자동 등록했습니다.\n\n*📌 감지된 업무 목록:*\n{req_summary}\n\n*⚙️ 조치 사항:*\n* 구글 캘린더 일정 등록 완료 (당일 18:00 ~ 19:00)\n* Google Tasks 할 일 목록 추가 완료"
                agent.send_webhook(notification)
    except Exception as e:
        print(f"[Worker] 자율 실시간 모니터링 실패: {e}")

if __name__ == "__main__":
    scheduler.add_job(job_morning_briefing, 'cron', day_of_week='mon-fri', hour=8, minute=45)
    scheduler.add_job(job_evening_briefing, 'cron', day_of_week='mon-fri', hour=17, minute=45)
    scheduler.add_job(job_check_deadlines, 'interval', minutes=10)
    scheduler.add_job(job_autonomous_monitoring, 'interval', minutes=2)
    
    print("[Worker] Background Scheduler Daemon Started.")
    scheduler.start()
