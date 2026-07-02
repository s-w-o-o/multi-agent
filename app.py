import streamlit as st
import threading
import time
import os
import glob
import json
from datetime import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from core.agent import AutonomousManagerAgent
from tools.mail_tools import has_new_unread_emails
import streamlit.components.v1 as components

st.set_page_config(page_title="INTERX Ultimate Multi-Agent v3", page_icon="🛸", layout="wide", initial_sidebar_state="collapsed")

# --- Agent Network Visualizer Helpers ---
def parse_active_connection(logs):
    if not logs:
        return None, None, None
    latest_log = logs[-1]
    agent = latest_log["agent"]
    msg = latest_log["message"]
    status = latest_log["status"]
    
    source = agent
    target = None
    
    msg_lower = msg.lower()
    if "mail" in msg_lower or "메일" in msg:
        target = "Mail Agent"
    elif "calendar" in msg_lower or "일정" in msg:
        target = "Calendar Agent"
    elif "task" in msg_lower or "할 일" in msg:
        target = "Tasks Agent"
    elif "research" in msg_lower or "검색" in msg:
        target = "Research Agent"
    elif "economy" in msg_lower or "경제" in msg:
        target = "Economy Agent"
    elif "chat" in msg_lower or "구글 챗" in msg:
        target = "Chat Agent"
    elif "security" in msg_lower or "보안" in msg:
        target = "Security Agent"
        
    return source, target, status

def render_agent_network_html(logs):
    source, target, status = parse_active_connection(logs)
    source_js = json.dumps(source)
    target_js = json.dumps(target)
    status_js = json.dumps(status)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                margin: 0;
                padding: 0;
                background-color: #161B22;
                overflow: hidden;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                border-radius: 12px;
                border: 1px solid #30363D;
                border-left: 3px solid #FFD700;
                box-sizing: border-box;
                height: 100vh;
            }}
            canvas {{
                display: block;
                background-color: #161B22;
            }}
        </style>
    </head>
    <body>
        <canvas id="networkCanvas"></canvas>
        <script>
            const canvas = document.getElementById('networkCanvas');
            const ctx = canvas.getContext('2d');
            
            const source = {source_js};
            const target = {target_js};
            const status = {status_js};
            
            const agents = [
                {{ name: "Manager Agent", icon: "🤖", color: "#00E676", isCenter: true }},
                {{ name: "Mail Agent", icon: "📩", color: "#FFB74D", angle: -125 }},
                {{ name: "Calendar Agent", icon: "📆", color: "#4FC3F7", angle: -90 }},
                {{ name: "Tasks Agent", icon: "✅", color: "#BA68C8", angle: -40 }},
                {{ name: "Research Agent", icon: "💡", color: "#FFF176", angle: 10 }},
                {{ name: "Economy Agent", icon: "📈", color: "#81C784", angle: 60 }},
                {{ name: "Chat Agent", icon: "💬", color: "#4DB6AC", angle: 125 }},
                {{ name: "Security Agent", icon: "🔒", color: "#58A6FF", angle: 180 }}
            ];
            
            function resizeCanvas() {{
                canvas.width = window.innerWidth;
                canvas.height = window.innerHeight || 350;
            }}
            window.addEventListener('resize', resizeCanvas);
            resizeCanvas();
            
            let dashOffset = 0;
            const isAnyActive = (source !== null);
            
            function animate() {{
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                
                const speed = isAnyActive ? 0.9 : 0.35;
                dashOffset += speed;
                if (dashOffset > 1000) dashOffset = 0;
                
                const cx = canvas.width / 2;
                const cy = canvas.height / 2;
                
                const isMobile = canvas.width < 500;
                const rx = isMobile ? canvas.width * 0.35 : Math.min(260, canvas.width * 0.35);
                const ry = isMobile ? canvas.height * 0.28 : Math.min(125, canvas.height * 0.33);
                
                // Position nodes with gentle floating animation (drifting inside card box)
                agents.forEach(agent => {{
                    let base_x, base_y;
                    if (agent.isCenter) {{
                        base_x = cx;
                        base_y = cy;
                    }} else {{
                        const rad = (agent.angle * Math.PI) / 180;
                        base_x = cx + rx * Math.cos(rad);
                        base_y = cy + ry * Math.sin(rad);
                    }}
                    
                    const phase = (agent.angle || 0) * 0.05;
                    const floatSpeed = 0.0012; // slow speed for smooth hover
                    const dx = Math.sin(Date.now() * floatSpeed + phase) * (agent.isCenter ? 3 : 6);
                    const dy = Math.cos(Date.now() * (floatSpeed * 0.8) + phase) * (agent.isCenter ? 3 : 5);
                    
                    agent.x = base_x + dx;
                    agent.y = base_y + dy;
                }});
                
                // 1. Draw Connections (Lines)
                agents.forEach(agent => {{
                    if (agent.isCenter) return;
                    
                    const manager = agents[0];
                    const is_active_connection = isAnyActive && (
                        (source === "Manager Agent" && target === agent.name) ||
                        (source === agent.name && target === "Manager Agent") ||
                        (source === agent.name && !target)
                    );
                    
                    ctx.beginPath();
                    ctx.moveTo(manager.x, manager.y);
                    ctx.lineTo(agent.x, agent.y);
                    
                    if (is_active_connection) {{
                        // Emphasized Active Connection (Gold)
                        ctx.strokeStyle = "#FFD700"; 
                        ctx.lineWidth = isMobile ? 4.5 : 6.0;
                        ctx.setLineDash([10, 15]);
                        ctx.lineDashOffset = -dashOffset * 2.0; // Flow much faster
                        ctx.shadowColor = "#FFD700";
                        ctx.shadowBlur = 22;
                    }} else {{
                        // Default/Background State: Colored static line (using agent color with opacity)
                        ctx.strokeStyle = agent.color + "66"; 
                        ctx.lineWidth = 1.5;
                        ctx.setLineDash([]);
                        ctx.lineDashOffset = 0;
                        ctx.shadowBlur = 0;
                    }}
                    ctx.stroke();
                    
                    // Draw flowing packet (thick circle) along the active connection
                    if (is_active_connection) {{
                        const t = (Date.now() / 1000) % 1.0; // cycle duration 1.0s (faster)
                        const px = manager.x + (agent.x - manager.x) * t;
                        const py = manager.y + (agent.y - manager.y) * t;
                        
                        ctx.beginPath();
                        ctx.arc(px, py, isMobile ? 6 : 9, 0, Math.PI * 2);
                        ctx.fillStyle = "#FFD700";
                        ctx.shadowColor = "#FFD700";
                        ctx.shadowBlur = 18;
                        ctx.fill();
                        ctx.shadowBlur = 0;
                    }}
                }});
                
                // Reset shadow for nodes
                ctx.shadowBlur = 0;
                ctx.setLineDash([]);
                
                // 2. Draw Nodes
                agents.forEach(agent => {{
                    const is_active_node = isAnyActive && (
                        agent.isCenter || (source === agent.name) || (target === agent.name)
                    );
                    const nodeRadius = isMobile ? (agent.isCenter ? 25 : 22) : (agent.isCenter ? 35 : 30);
                    
                    // Draw outer shiny ring for active node
                    if (is_active_node) {{
                        const pulseRing = nodeRadius + (isMobile ? 6 : 9) + Math.sin(Date.now() / 150) * (isMobile ? 2 : 4);
                        ctx.beginPath();
                        ctx.arc(agent.x, agent.y, pulseRing, 0, Math.PI * 2);
                        ctx.strokeStyle = "rgba(255, 215, 0, 0.75)";
                        ctx.lineWidth = isMobile ? 3.0 : 4.5;
                        ctx.shadowColor = "#FFD700";
                        ctx.shadowBlur = 25;
                        ctx.stroke();
                        ctx.shadowBlur = 0;
                    }}
                    
                    ctx.beginPath();
                    ctx.arc(agent.x, agent.y, nodeRadius, 0, Math.PI * 2);
                    
                    if (is_active_node) {{
                        // Active Node (Gold glow)
                        ctx.fillStyle = "#161B22";
                        ctx.strokeStyle = "#FFD700";
                        ctx.lineWidth = 5.5;
                        ctx.shadowColor = "#FFD700";
                        ctx.shadowBlur = 32;
                    }} else {{
                        // Default State: Clean, simple, single border with the agent's theme color (no glow)
                        ctx.fillStyle = "#0D1117";
                        ctx.strokeStyle = agent.color;
                        ctx.lineWidth = 1.5;
                        ctx.shadowBlur = 0;
                    }}
                    ctx.fill();
                    ctx.stroke();
                    
                    ctx.shadowBlur = 0;
                    
                    // Draw Icon
                    ctx.font = isMobile ? "16px Arial" : "22px Arial";
                    ctx.textAlign = "center";
                    ctx.textBaseline = "middle";
                    ctx.fillText(agent.icon, agent.x, agent.y);
                    
                    // Draw Name Label
                    ctx.font = isMobile ? "9px 'Segoe UI', sans-serif" : "bold 11px 'Segoe UI', sans-serif";
                    ctx.fillStyle = is_active_node ? "#FFD700" : "#8B949E"; // Active is gold, others are grey (original design)
                    
                    const labelY = agent.y + (isMobile ? nodeRadius + 14 : nodeRadius + 20);
                    ctx.fillText(agent.name.replace(" Agent", ""), agent.x, labelY);
                }});
                
                requestAnimationFrame(animate);
            }}
            
            animate();
        </script>
    </body>
    </html>
    """
    return html_content


# Simple Password Authentication for Secure Tunnel Access
def check_password():
    """Returns True if the user had the correct password."""
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        correct_password = os.getenv("DASHBOARD_PASSWORD", "interx123!")
        if st.session_state["password"] == correct_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.subheader("🛸 INTERX AGI Agent Dashboard Security")
        st.text_input(
            "Access Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        st.subheader("🛸 INTERX AGI Agent Dashboard Security")
        st.text_input(
            "Access Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Incorrect password. Please try again.")
        return False
    else:
        return True

if not check_password():
    st.stop()

# Client-side mobile viewport detection and query param redirection
components.html(
    """
    <script>
        const parentUrl = new URL(window.parent.location.href);
        const isMobileViewport = window.parent.innerWidth <= 768;
        const deviceParam = parentUrl.searchParams.get('device');
        
        if (isMobileViewport && deviceParam !== 'mobile') {
            parentUrl.searchParams.set('device', 'mobile');
            window.parent.location.href = parentUrl.toString();
        } else if (!isMobileViewport && deviceParam === 'mobile') {
            parentUrl.searchParams.delete('device');
            window.parent.location.href = parentUrl.toString();
        }
    </script>
    """,
    height=0,
    width=0
)

# Cyberpunk Premium Dark UI Style
st.markdown("""
<style>
    /* 1. Header & Base Theming */
    header[data-testid="stHeader"],
    [data-testid="stAppHeader"],
    .stAppHeader,
    div[data-testid="stDecoration"] {
        display: none !important;
        height: 0px !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    .block-container {
        padding-top: 0.75rem !important;
        padding-bottom: 3rem !important;
        margin-top: 0px !important;
    }
    h1 {
        margin-top: 0px !important;
        padding-top: 0px !important;
    }
    .report-card h1 {
        margin-top: 30px !important;
        padding-top: 0px !important;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Cyberpunk Styled Cards */
    .report-card {
        background-color: #0D1117;
        padding: 35px 40px;
        border-radius: 16px;
        border: 1px solid #30363D;
        box-shadow: 0 10px 30px rgba(0,0,0,0.6), 0 0 15px rgba(88, 166, 255, 0.1);
        margin-top: 15px;
        margin-bottom: 40px;
    }
    .report-card h1, .report-card h2, .report-card h3 {
        color: #58A6FF !important;
        border-bottom: 1px solid #30363D;
        padding-bottom: 10px;
        margin-top: 30px;
        margin-bottom: 15px;
        font-family: 'Pretendard', 'Segoe UI', sans-serif;
    }
    .report-card h1 { font-size: 1.8rem !important; text-shadow: 0 0 10px rgba(88, 166, 255, 0.4); }
    .report-card h2 { font-size: 1.5rem !important; }
    .report-card h3 { font-size: 1.25rem !important; color: #79C0FF !important; border-bottom: none; }
    .report-card p, .report-card li {
        font-size: 1.05rem !important;
        line-height: 1.7 !important;
        color: #C9D1D9 !important;
    }
    .report-card blockquote {
        border-left: 4px solid #00E676;
        background-color: #161B22;
        padding: 15px 20px;
        border-radius: 6px;
        margin-left: 0;
        margin-top: 20px;
        font-style: normal;
        font-size: 1rem !important;
        box-shadow: 0 0 10px rgba(0, 230, 118, 0.05);
    }
    .report-card hr {
        border-color: #30363D;
        margin: 30px 0;
    }
    
    /* Live Status Board Animation */
    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 230, 118, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(0, 230, 118, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 230, 118, 0); }
    }
    @keyframes ledBlink {
        0% { opacity: 0.35; transform: scale(0.85); }
        50% { opacity: 1; transform: scale(1.15); box-shadow: 0 0 8px #00E676, 0 0 15px #00E676; }
        100% { opacity: 0.35; transform: scale(0.85); }
    }
    @keyframes ledBlinkBlue {
        0% { opacity: 0.35; transform: scale(0.85); }
        50% { opacity: 1; transform: scale(1.15); box-shadow: 0 0 8px #58A6FF, 0 0 15px #58A6FF; }
        100% { opacity: 0.35; transform: scale(0.85); }
    }
    @keyframes borderPulse {
        0% { border-color: rgba(48, 54, 61, 0.8); box-shadow: 0 4px 6px rgba(0, 0, 0, 0.4), 0 0 2px rgba(0, 230, 118, 0.05); }
        50% { border-color: rgba(0, 230, 118, 0.8); box-shadow: 0 4px 6px rgba(0, 0, 0, 0.4), 0 0 12px rgba(0, 230, 118, 0.3); }
        100% { border-color: rgba(48, 54, 61, 0.8); box-shadow: 0 4px 6px rgba(0, 0, 0, 0.4), 0 0 2px rgba(0, 230, 118, 0.05); }
    }
    @keyframes borderPulseBlue {
        0% { border-color: rgba(48, 54, 61, 0.8); box-shadow: 0 4px 6px rgba(0, 0, 0, 0.4), 0 0 2px rgba(88, 166, 255, 0.05); }
        50% { border-color: rgba(88, 166, 255, 0.8); box-shadow: 0 4px 6px rgba(0, 0, 0, 0.4), 0 0 12px rgba(88, 166, 255, 0.3); }
        100% { border-color: rgba(48, 54, 61, 0.8); box-shadow: 0 4px 6px rgba(0, 0, 0, 0.4), 0 0 2px rgba(88, 166, 255, 0.05); }
    }
    .status-dot {
        height: 8px;
        width: 8px;
        background-color: #00E676;
        border-radius: 50%;
        display: inline-block;
        margin-right: 6px;
        animation: pulse 2s infinite;
    }
    .agents-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 10px;
        margin-bottom: 25px;
    }
    .agent-card {
        position: relative;
        background-color: #161B22;
        border-left: 3px solid #00E676;
        padding: 6px 12px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.4), 0 0 10px rgba(0, 230, 118, 0.05);
        border-top: 1px solid #30363D;
        border-right: 1px solid #30363D;
        border-bottom: 1px solid #30363D;
        min-height: 52px;
    }
    .agent-card.security {
        border-left: 3px solid #58A6FF;
    }
    .agent-icon {
        font-size: 1.25rem;
        margin-right: 10px;
        flex-shrink: 0;
    }
    .agent-info {
        min-width: 0;
        flex: 1;
    }
    .agent-info h4 {
        margin: 0;
        color: #FFFFFF;
        font-size: 0.85rem;
        font-weight: 600;
        text-shadow: 0 0 5px rgba(255,255,255,0.1);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .agent-info p {
        margin: 0;
        color: #8B949E;
        font-size: 0.72rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    /* Neon Warning Alerts */
    .neon-alert {
        background-color: rgba(248, 81, 73, 0.1);
        border: 1px solid #F85149;
        box-shadow: 0 0 15px rgba(248, 81, 73, 0.15);
        padding: 15px 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        color: #FF7B72;
        font-weight: bold;
    }
    
    /* Responsive Mobile Tab Bar & Card Adjustments */
    @media (max-width: 768px) {
        /* Hide default Streamlit header and adjust padding on mobile */
        [data-testid="stHeader"],
        [data-testid="stAppHeader"],
        .stAppHeader {
            display: none !important;
            height: 0px !important;
            padding: 0 !important;
        }
        .main .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 6rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }

        /* Title scaling & Neon Glow */
        h1 {
            font-size: 1.45rem !important;
            text-align: center;
            color: #58A6FF !important;
            text-shadow: 0 0 10px rgba(88, 166, 255, 0.4);
            margin-top: 0px !important;
            padding-top: 0px !important;
            margin-bottom: 12px !important;
        }
        div.stMarkdown p {
            font-size: 0.85rem !important;
            text-align: center;
            margin-bottom: 15px !important;
        }
        
        /* Fixed Bottom Tab Bar on Mobile */
        div[data-baseweb="tab-list"] {
            position: fixed !important;
            bottom: 0 !important;
            left: 0 !important;
            width: 100% !important;
            background-color: #0D1117 !important;
            border-top: 1px solid #30363D !important;
            z-index: 99999 !important;
            display: flex !important;
            justify-content: space-around !important;
            padding: 8px 0 !important;
            box-shadow: 0 -5px 20px rgba(0,0,0,0.6) !important;
        }
        
        button[data-baseweb="tab"] {
            flex: 1 !important;
            text-align: center !important;
            font-size: 0.85rem !important;
            padding: 10px 2px !important;
            background-color: transparent !important;
            color: #8B949E !important;
            border: none !important;
        }
        
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #58A6FF !important;
            border-bottom: 2px solid #58A6FF !important;
            font-weight: bold !important;
            text-shadow: 0 0 8px rgba(88, 166, 255, 0.5) !important;
        }
        
        div[data-baseweb="tab-panel"] {
            margin-bottom: 70px !important;
            padding: 5px !important;
        }
 
        .report-card {
            padding: 20px 15px !important;
            margin-top: 10px !important;
            margin-bottom: 20px !important;
            border-radius: 12px !important;
        }
        
        /* Grid styling for 4x2 Agent Board on Mobile */
        .agents-grid {
            grid-template-columns: repeat(4, 1fr) !important;
            gap: 8px !important;
            margin-bottom: 15px !important;
        }
        
        .agent-card {
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 10px 2px !important;
            text-align: center !important;
            border-radius: 8px !important;
            border: 1px solid rgba(48, 54, 61, 0.8) !important;
            border-left: 3px solid rgba(0, 230, 118, 0.8) !important;
            min-height: 70px !important;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.4) !important;
            margin-bottom: 0 !important;
            animation: borderPulse 3s infinite ease-in-out;
        }
        
        .agent-card.security {
            border-left: 3px solid rgba(88, 166, 255, 0.8) !important;
            animation: borderPulseBlue 3s infinite ease-in-out;
        }
        
        /* Dynamic Breathing LED Dot */
        .agent-card::after {
            content: "";
            position: absolute;
            top: 6px;
            right: 6px;
            width: 5px;
            height: 5px;
            background-color: #00E676;
            border-radius: 50%;
            animation: ledBlink 1.8s infinite ease-in-out;
        }
        
        .agent-card.security::after {
            background-color: #58A6FF;
            animation: ledBlinkBlue 1.8s infinite ease-in-out;
        }
        
        .agent-icon {
            font-size: 1.8rem !important;
            margin-right: 0 !important;
            margin-bottom: 0 !important;
        }
        
        /* Hide all text inside agent cards on mobile */
        .agent-info {
            display: none !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- Manager Agent Setup ---
@st.cache_resource
def init_system():
    return AutonomousManagerAgent()

agent = init_system()

# --- Background Scheduler Setup ---
@st.cache_resource
def start_background_scheduler():
    scheduler = BackgroundScheduler(timezone=pytz.timezone("Asia/Seoul"))
    
    def job_morning_briefing():
        if datetime.now(pytz.timezone("Asia/Seoul")).weekday() in [5, 6]: return
        print("[Worker] 실행: 자율 아침 보고")
        prompt = "지금은 아침 출근 시간입니다. 1. 읽지 않은 메일을 확인하고 필요한 조치를 취하세요. 2. 오늘 일정을 확인하세요. 3. 미완료된 할 일을 확인하세요. 4. 밤사이 증시(KOSPI, KOSDAQ, S&P 500, 나스닥, 환율)와 기술 트렌드 뉴스를 검색하여 브리핑해주세요. 이를 종합하여 최종 아침 보고서를 작성하세요."
        try:
            report = agent.run_task(prompt)
            agent.send_webhook(report)
        except Exception as e:
            print(f"[Worker] 아침 보고 실패: {e}")

    def job_evening_briefing():
        if datetime.now(pytz.timezone("Asia/Seoul")).weekday() in [5, 6]: return
        print("[Worker] 실행: 자율 저녁 보고")
        prompt = "지금은 퇴근 시간입니다. 1. 읽지 않은 메일을 확인하고 초안을 작성하세요. 2. 내일 일정을 확인하세요. 3. 미완료된 할 일들을 점검하세요. 저녁 시간이므로 새로운 할 일을 등록하지 마세요. 오늘 하루 성과와 내일의 준비에 초점을 맞춰 최종 저녁 보고서를 작성하세요."
        try:
            report = agent.run_task(prompt)
            agent.send_webhook(report)
        except Exception as e:
            print(f"[Worker] 저녁 보고 실패: {e}")

    def job_check_deadlines():
        if datetime.now(pytz.timezone("Asia/Seoul")).weekday() in [5, 6]: return
        print("[Worker] 실행: 할 일 마감 시간 점검")
        try:
            status = agent.tasks_agent.check_deadlines_and_notify()
            print(f"[Worker] 할 일 마감 점검 완료: {status}")
        except Exception as e:
            print(f"[Worker] 할 일 마감 점검 실패: {e}")

    def job_autonomous_monitoring():
        if datetime.now(pytz.timezone("Asia/Seoul")).weekday() in [5, 6]: return
        print("[Worker] 실행: 자율 실시간 메일 모니터링 (2분 주기)")
        try:
            if not has_new_unread_emails():
                print("[Worker] [Scheduler] 신규 읽지 않은 메일이 없습니다. (LLM 스킵)")
                return
                
            prompt = "이메일을 확인하여 우주현 책임에게 전달된 신규 업무 조치/협조/확인 요청 건이 있는지 검사하고, 발견 시 오늘 18:00~19:00 구글 캘린더 일정 및 Google Tasks 할 일 목록에 각각 즉시 자동 등록하세요."
            report = agent.run_task(prompt)
            
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

    scheduler.add_job(job_morning_briefing, 'cron', day_of_week='mon-fri', hour=8, minute=45)
    scheduler.add_job(job_evening_briefing, 'cron', day_of_week='mon-fri', hour=17, minute=45)
    scheduler.add_job(job_check_deadlines, 'interval', minutes=10)
    scheduler.add_job(job_autonomous_monitoring, 'interval', minutes=2)
    
    scheduler.start()
    print("[Scheduler] Background Scheduler Thread Started inside app.py process.")
    return scheduler

scheduler = start_background_scheduler()

# --- Warning Session State ---
if "has_warning" not in st.session_state:
    st.session_state.has_warning = False
if "warning_message" not in st.session_state:
    st.session_state.warning_message = ""

# --- UI Components ---
def render_desktop_ui():
    if st.session_state.get("show_success_toast", False):
        st.toast("임무가 완료되었습니다! 최신 업무 브리핑 보고서 탭을 확인해 주세요.", icon="✅")
        st.session_state.show_success_toast = False

    st.title("🛸 INTERX Ultimate Multi-Agent System (v3)")
    st.markdown("수석 비서 매니저와 6대 전문 에이전트들이 `우주현 책임`님을 위해 실시간 연동 및 자율 비서 액션을 수행합니다. `(자동 브리핑: 평일 08:45 AM / 17:45 PM)`")

    # Real-time Warning Notification
    if st.session_state.has_warning:
        st.markdown(f"""
        <div class="neon-alert">
            {st.session_state.warning_message}
            <span style="float:right; cursor:pointer;" onclick="window.location.reload();">Dismiss</span>
        </div>
        """, unsafe_allow_html=True)
        if st.button("경고 알림 해제"):
            st.session_state.has_warning = False
            st.session_state.warning_message = ""
            st.rerun()

    # --- Status Board & Manual Override & Archive Layout ---
    tab_control, tab_report, tab_archive = st.tabs(["📟 Control Center", "📄 Current Report", "🗄️ Briefing Archive"])

    with tab_control:
        col_left, col_right = st.columns([1.2, 1.0])
        
        with col_left:
            st.markdown("### 📡 Active Agent Control Center")
            st.markdown("""
            <div class="agents-grid">
                <div class="agent-card manager">
                    <div class="agent-icon">
                        <img src="https://cdn.jsdelivr.net/gh/microsoft/fluentui-emoji@latest/assets/Robot/3D/robot_3d.png" width="24" height="24" style="vertical-align: middle; filter: drop-shadow(0 0 3px rgba(0, 230, 118, 0.4)); display: inline-block;">
                    </div>
                    <div class="agent-info">
                        <h4>Manager Agent</h4>
                        <p><span class="status-dot"></span>Active & Orchestrating</p>
                    </div>
                </div>
                <div class="agent-card mail">
                    <div class="agent-icon">📩</div>
                    <div class="agent-info">
                        <h4>Mail Agent</h4>
                        <p><span class="status-dot"></span>Mail Monitoring</p>
                    </div>
                </div>
                <div class="agent-card calendar">
                    <div class="agent-icon">📆</div>
                    <div class="agent-info">
                        <h4>Calendar Agent</h4>
                        <p><span class="status-dot"></span>Schedule Operations</p>
                    </div>
                </div>
                <div class="agent-card tasks">
                    <div class="agent-icon">✅</div>
                    <div class="agent-info">
                        <h4>Tasks Agent</h4>
                        <p><span class="status-dot"></span>Deadline Tracking</p>
                    </div>
                </div>
                <div class="agent-card research">
                    <div class="agent-icon">💡</div>
                    <div class="agent-info">
                        <h4>Research Agent</h4>
                        <p><span class="status-dot"></span>Global Tech Research</p>
                    </div>
                </div>
                <div class="agent-card economy">
                    <div class="agent-icon">📈</div>
                    <div class="agent-info">
                        <h4>Economy Agent</h4>
                        <p><span class="status-dot"></span>Market Analytics</p>
                    </div>
                </div>
                <div class="agent-card chat">
                    <div class="agent-icon">💬</div>
                    <div class="agent-info">
                        <h4>Chat Agent</h4>
                        <p><span class="status-dot"></span>Google Chat Gateway</p>
                    </div>
                </div>
                <div class="agent-card security">
                    <div class="agent-icon">🔒</div>
                    <div class="agent-info">
                        <h4>Security Agent</h4>
                        <p style="color: #58A6FF;"><span class="status-dot" style="background-color: #58A6FF; animation: none;"></span>Credential Shield Active</p>
                    </div>
                </div>
            </div>
            
            <script>
                (function() {
                    window.syncAgentViewHeight = function() {
                        const grid = document.querySelector('.agents-grid');
                        if (!grid) return;
                        
                        const leftCol = grid.closest('[data-testid="column"]');
                        if (!leftCol) return;
                        
                        const rightCol = leftCol.nextElementSibling;
                        if (!rightCol) return;
                        
                        const iframe = rightCol.querySelector('iframe');
                        if (!iframe) return;
                        
                        const gridHeight = grid.getBoundingClientRect().height;
                        if (gridHeight > 0) {
                            iframe.style.setProperty('height', gridHeight + 'px', 'important');
                            iframe.setAttribute('height', gridHeight);
                            
                            // Traverse up from iframe to set height on Streamlit components container divs
                            let parent = iframe.parentElement;
                            while (parent && parent !== rightCol) {
                                if (parent.style.height || parent.getAttribute('data-testid') === 'stHtml') {
                                    parent.style.setProperty('height', gridHeight + 'px', 'important');
                                }
                                parent = parent.parentElement;
                            }
                        }
                    };

                    // Re-observe grid elements on each render
                    if (window.agentViewObserver) {
                        window.agentViewObserver.disconnect();
                    }
                    window.agentViewObserver = new ResizeObserver(() => {
                        if (window.syncAgentViewHeight) window.syncAgentViewHeight();
                    });

                    const gridEl = document.querySelector('.agents-grid');
                    if (gridEl) {
                        window.agentViewObserver.observe(gridEl);
                        window.syncAgentViewHeight();
                    }

                    if (!window.agentViewIntervalInitialized) {
                        window.agentViewIntervalInitialized = true;
                        window.addEventListener('resize', () => {
                            if (window.syncAgentViewHeight) window.syncAgentViewHeight();
                        });
                        setInterval(() => {
                            if (window.syncAgentViewHeight) window.syncAgentViewHeight();
                        }, 500);
                    }
                })();
            </script>
            """, unsafe_allow_html=True)
            
        with col_right:
            st.markdown("### 🕸️ Agent View")
            # Renders the network graph directly below the agent grid using a placeholder
            network_graph_placeholder = st.empty()
            logs_to_render = st.session_state.get("orchestration_logs", [])
            with network_graph_placeholder:
                components.html(render_agent_network_html(logs_to_render), height=300)

        st.divider()

        # --- Manual Override ---
        st.subheader("🛠️ 자율 협업 명령 및 인터랙티브 질문 (Interactive Prompt)")
        st.markdown("질문을 하거나 능동적 액션(예: 일정 등록, 구글 챗 발송 등)을 지시하세요. 에이전트들이 상호 협업하여 즉시 실행합니다.")
        # Define key suffix for text area to allow programmatically clearing it
        if "prompt_key_suffix" not in st.session_state:
            st.session_state.prompt_key_suffix = 0

        widget_key = f"user_prompt_input_{st.session_state.prompt_key_suffix}"
        user_prompt = st.text_area("명령 입력:", height=100, label_visibility="collapsed", placeholder="예: 내일 오후 3시에 [심텍] 회의 등록해주고 Google Chat 개발팀 스페이스에 회의 일정이 등록되었다고 메시지 전송해줘.", key=widget_key)

        if st.button("실행 (Run Agent Tool-Chain)", type="primary"):
            if user_prompt:
                # Clear simulation logs to show actual active logs
                if "sim_logs" in st.session_state:
                    del st.session_state.sim_logs
                
                st.session_state.orchestration_logs = []
                if "completed_logs" in st.session_state:
                    del st.session_state.completed_logs
                log_placeholder = st.empty()
                
                def local_callback(agent_name, message, status):
                    if "orchestration_logs" not in st.session_state:
                        st.session_state.orchestration_logs = []
                        
                    tz = pytz.timezone('Asia/Seoul')
                    st.session_state.orchestration_logs.append({
                        "timestamp": datetime.now(tz).strftime("%H:%M:%S"),
                        "agent": agent_name,
                        "message": message,
                        "status": status
                    })
                    
                    # Update the top graph view live
                    with network_graph_placeholder:
                        components.html(render_agent_network_html(st.session_state.orchestration_logs), height=300)
                    
                    # Re-render step-by-step logs dynamically in the placeholder
                    with log_placeholder.container():
                        st.markdown("### 📡 에이전트 협업 오케스트레이션 라이브 플로우 (Live Steps)")
                        for log in st.session_state.orchestration_logs:
                            icon = "ℹ️"
                            if log["status"] == "running":
                                icon = "⚙️"
                            elif log["status"] == "success":
                                icon = "✅"
                            elif log["status"] == "warning":
                                icon = "⚠️"
                                
                            color = "#A0AABF"
                            if log["status"] == "running":
                                color = "#58A6FF"
                            elif log["status"] == "success":
                                color = "#00E676"
                            elif log["status"] == "warning":
                                color = "#FFD600"
                                
                            st.markdown(
                                f"""
                                <div style="background-color: #161B22; padding: 12px 18px; border-left: 4px solid {color}; border-radius: 8px; margin-bottom: 8px; border: 1px solid #30363D;">
                                    <strong style="color: {color}; font-size: 0.95rem;">{icon} [{log['timestamp']}] {log['agent']}</strong>
                                    <div style="color: #C9D1D9; font-size: 0.9rem; margin-top: 5px; line-height: 1.4;">{log['message']}</div>
                                </div>
                                """, 
                                unsafe_allow_html=True
                            )

                with st.spinner("수석 비서가 목표를 분석하고 에이전트들을 기동하여 조치 중입니다..."):
                    try:
                        result = agent.run_task(user_prompt, log_callback=local_callback)
                        st.success("임무 완료!")
                        st.session_state["latest_report"] = result
                        
                        # Save completed logs for rendering after rerun
                        st.session_state.completed_logs = list(st.session_state.orchestration_logs)
                        st.session_state.orchestration_logs = []
                        with network_graph_placeholder:
                            components.html(render_agent_network_html([]), height=300)
                            
                        # Increment prompt key suffix to force redraw a new empty text area
                        st.session_state.prompt_key_suffix += 1
                        
                        st.session_state.show_success_toast = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류 발생: {e}")
            else:
                st.warning("명령을 입력해주세요.")

        # Show completed logs and latest report in the Control Center tab after execution finishes
        if st.session_state.get("completed_logs"):
            st.markdown("### 📡 에이전트 협업 오케스트레이션 라이브 플로우 (Execution Steps)")
            for log in st.session_state.completed_logs:
                icon = "ℹ️"
                if log["status"] == "running": icon = "⚙️"
                elif log["status"] == "success": icon = "✅"
                elif log["status"] == "warning": icon = "⚠️"
                
                color = "#A0AABF"
                if log["status"] == "running": color = "#58A6FF"
                elif log["status"] == "success": color = "#00E676"
                elif log["status"] == "warning": color = "#FFD600"
                
                st.markdown(
                    f"""
                    <div style="background-color: #161B22; padding: 12px 18px; border-left: 4px solid {color}; border-radius: 8px; margin-bottom: 8px; border: 1px solid #30363D;">
                        <strong style="color: {color}; font-size: 0.95rem;">{icon} [{log['timestamp']}] {log['agent']}</strong>
                        <div style="color: #C9D1D9; font-size: 0.9rem; margin-top: 5px; line-height: 1.4;">{log['message']}</div>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

        if st.session_state.get("completed_logs") and st.session_state.get("latest_report"):
            report_content = st.session_state.latest_report
            if report_content != "아직 생성된 보고서가 없습니다.":
                st.markdown("### 📄 최신 업무 브리핑 보고서 (Result)")
                st.markdown(f"<div class='report-card'>{report_content}</div>", unsafe_allow_html=True)

    with tab_report:
        st.markdown("### 📄 최신 업무 브리핑 보고서 (Latest Briefing)")
        
        # Check session state first, otherwise load latest report from file
        latest_report_content = "아직 생성된 보고서가 없습니다."
        try:
            log_files = sorted(glob.glob("logs/report_*.txt"), reverse=True)
            if log_files:
                with open(log_files[0], "r", encoding="utf-8") as f:
                    latest_report_content = f.read()
        except Exception as e:
            latest_report_content = f"보고서를 불러올 수 없습니다: {e}"
            
        report_to_show = st.session_state.get("latest_report", latest_report_content)
        st.markdown(f"<div class='report-card'>{report_to_show}</div>", unsafe_allow_html=True)

    with tab_archive:
        st.markdown("### 📝 최근 업무 브리핑 아카이브 (Daily Briefing Archive)")
        try:
            log_files = sorted(glob.glob("logs/report_*.txt"), reverse=True)
            if log_files:
                selected_log = st.selectbox("지난 보고서 열람 (이력 확인)", log_files, format_func=lambda x: os.path.basename(x))
                with open(selected_log, "r", encoding="utf-8") as f:
                    content = f.read()
                st.markdown(f"<div class='report-card'>{content}</div>", unsafe_allow_html=True)
            else:
                st.info("아직 생성된 보고서가 없습니다.")
        except Exception as e:
            st.error(f"로그를 불러올 수 없습니다: {e}")

def render_mobile_ui():
    st.markdown("""
    <style>
        /* Hide default Streamlit header and adjust padding on mobile */
        [data-testid="stHeader"],
        [data-testid="stAppHeader"],
        .stAppHeader {
            display: none !important;
            height: 0px !important;
            padding: 0 !important;
        }
        .main .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 6rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }

        /* Mobile Specific Overrides */
        .report-card {
            padding: 16px 14px !important;
            margin-top: 10px !important;
            margin-bottom: 20px !important;
            border-radius: 10px !important;
        }
        .report-card h1 { font-size: 1.35rem !important; }
        .report-card h2 { font-size: 1.15rem !important; }
        .report-card h3 { font-size: 1.0rem !important; }
        .report-card p, .report-card li { font-size: 0.9rem !important; line-height: 1.5 !important; }
        
        
        /* Sticky bottom tabs */
        div[data-baseweb="tab-list"] {
            position: fixed !important;
            bottom: 0 !important;
            left: 0 !important;
            width: 100% !important;
            background-color: #0D1117 !important;
            border-top: 1px solid #30363D !important;
            z-index: 99999 !important;
            display: flex !important;
            justify-content: space-around !important;
            padding: 6px 0 !important;
            box-shadow: 0 -5px 15px rgba(0,0,0,0.6) !important;
        }
        button[data-baseweb="tab"] {
            flex: 1 !important;
            text-align: center !important;
            font-size: 0.8rem !important;
            padding: 8px 2px !important;
            background-color: transparent !important;
            color: #8B949E !important;
            border: none !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #58A6FF !important;
            border-bottom: 2px solid #58A6FF !important;
            font-weight: bold !important;
        }
        div[data-baseweb="tab-panel"] {
            margin-bottom: 60px !important;
            padding: 5px !important;
        }
    </style>
    """, unsafe_allow_html=True)

    if st.session_state.get("show_success_toast_mobile", False):
        st.toast("임무가 완료되었습니다! 최신 업무 브리핑 탭을 확인해 주세요.", icon="✅")
        st.session_state.show_success_toast_mobile = False

    st.title("🛸 INTERX Mobile v3")
    
    # Real-time Warning Notification for mobile
    if st.session_state.has_warning:
        st.markdown(f"""
        <div class="neon-alert" style="padding: 10px 15px; font-size: 0.85rem;">
            {st.session_state.warning_message}
        </div>
        """, unsafe_allow_html=True)
        if st.button("경고 해제", use_container_width=True):
            st.session_state.has_warning = False
            st.session_state.warning_message = ""
            st.rerun()

    tab_control, tab_report, tab_archive = st.tabs(["📟 Control", "📄 Report", "🗄️ Archive"])
    
    with tab_control:
        st.markdown("""
        <div class="agents-grid">
            <div class="agent-card manager">
                <div class="agent-icon">
                    <img src="https://cdn.jsdelivr.net/gh/microsoft/fluentui-emoji@latest/assets/Robot/3D/robot_3d.png" width="32" height="32" style="vertical-align: middle; filter: drop-shadow(0 0 3px rgba(0, 230, 118, 0.4)); display: inline-block;">
                </div>
                <div class="agent-info">
                    <h4>Manager</h4>
                </div>
            </div>
            <div class="agent-card mail">
                <div class="agent-icon">📩</div>
                <div class="agent-info">
                    <h4>Mail</h4>
                </div>
            </div>
            <div class="agent-card calendar">
                <div class="agent-icon">📆</div>
                <div class="agent-info">
                    <h4>Calendar</h4>
                </div>
            </div>
            <div class="agent-card tasks">
                <div class="agent-icon">✅</div>
                <div class="agent-info">
                    <h4>Tasks</h4>
                </div>
            </div>
            <div class="agent-card research">
                <div class="agent-icon">💡</div>
                <div class="agent-info">
                    <h4>Research</h4>
                </div>
            </div>
            <div class="agent-card economy">
                <div class="agent-icon">📈</div>
                <div class="agent-info">
                    <h4>Economy</h4>
                </div>
            </div>
            <div class="agent-card chat">
                <div class="agent-icon">💬</div>
                <div class="agent-info">
                    <h4>Chat</h4>
                </div>
            </div>
            <div class="agent-card security">
                <div class="agent-icon">🔒</div>
                <div class="agent-info">
                    <h4>Security</h4>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Renders the network graph directly below the agent grid on mobile using a placeholder
        network_graph_placeholder_mobile = st.empty()
        logs_to_render = st.session_state.get("orchestration_logs", [])
        with network_graph_placeholder_mobile:
            components.html(render_agent_network_html(logs_to_render), height=320)

        st.markdown("##### 🛠️ 자율 협업 명령")
        # Define key suffix for text area to allow programmatically clearing it on mobile
        if "prompt_key_suffix_mobile" not in st.session_state:
            st.session_state.prompt_key_suffix_mobile = 0

        widget_key_mobile = f"user_prompt_input_mobile_{st.session_state.prompt_key_suffix_mobile}"
        user_prompt = st.text_area("명령 입력:", height=75, label_visibility="collapsed", placeholder="명령을 입력하세요...", key=widget_key_mobile)
        
        if st.button("실행 (Run Agent)", type="primary", use_container_width=True):
            if user_prompt:
                # Clear simulation logs to show actual active logs
                if "sim_logs" in st.session_state:
                    del st.session_state.sim_logs
                
                st.session_state.orchestration_logs = []
                if "completed_logs_mobile" in st.session_state:
                    del st.session_state.completed_logs_mobile
                log_placeholder = st.empty()
                
                def local_callback(agent_name, message, status):
                    if "orchestration_logs" not in st.session_state:
                        st.session_state.orchestration_logs = []
                    tz = pytz.timezone('Asia/Seoul')
                    st.session_state.orchestration_logs.append({
                        "timestamp": datetime.now(tz).strftime("%H:%M:%S"),
                        "agent": agent_name,
                        "message": message,
                        "status": status
                    })
                    
                    # Update the top graph view live on mobile
                    with network_graph_placeholder_mobile:
                        components.html(render_agent_network_html(st.session_state.orchestration_logs), height=320)
                    
                    with log_placeholder.container():
                        for log in st.session_state.orchestration_logs:
                            icon = "ℹ️"
                            if log["status"] == "running": icon = "⚙️"
                            elif log["status"] == "success": icon = "✅"
                            elif log["status"] == "warning": icon = "⚠️"
                                
                            color = "#A0AABF"
                            if log["status"] == "running": color = "#58A6FF"
                            elif log["status"] == "success": color = "#00E676"
                            elif log["status"] == "warning": color = "#FFD600"
                                
                            st.markdown(
                                f"""
                                <div style="background-color: #161B22; padding: 8px 12px; border-left: 3px solid {color}; border-radius: 6px; margin-bottom: 6px; border: 1px solid #30363D;">
                                    <strong style="color: {color}; font-size: 0.75rem;">{icon} [{log['timestamp']}] {log['agent']}</strong>
                                    <div style="color: #C9D1D9; font-size: 0.75rem; margin-top: 3px; line-height: 1.3;">{log['message']}</div>
                                </div>
                                """, 
                                unsafe_allow_html=True
                            )

                with st.spinner("에이전트 실행 중..."):
                    try:
                        result = agent.run_task(user_prompt, log_callback=local_callback)
                        st.success("완료!")
                        st.session_state["latest_report"] = result
                        
                        # Save completed logs for rendering after rerun
                        st.session_state.completed_logs_mobile = list(st.session_state.orchestration_logs)
                        st.session_state.orchestration_logs = []
                        with network_graph_placeholder_mobile:
                            components.html(render_agent_network_html([]), height=320)
                            
                        # Increment mobile prompt key suffix to force redraw a new empty text area
                        st.session_state.prompt_key_suffix_mobile += 1
                        
                        st.session_state.show_success_toast_mobile = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
            else:
                st.warning("명령을 입력해주세요.")

        # Show completed logs and latest report in the mobile Control Center tab after execution finishes
        if st.session_state.get("completed_logs_mobile"):
            st.markdown("##### 📡 에이전트 협업 라이브 플로우")
            for log in st.session_state.completed_logs_mobile:
                icon = "ℹ️"
                if log["status"] == "running": icon = "⚙️"
                elif log["status"] == "success": icon = "✅"
                elif log["status"] == "warning": icon = "⚠️"
                
                color = "#A0AABF"
                if log["status"] == "running": color = "#58A6FF"
                elif log["status"] == "success": color = "#00E676"
                elif log["status"] == "warning": color = "#FFD600"
                
                st.markdown(
                    f"""
                    <div style="background-color: #161B22; padding: 8px 12px; border-left: 3px solid {color}; border-radius: 6px; margin-bottom: 6px; border: 1px solid #30363D;">
                        <strong style="color: {color}; font-size: 0.75rem;">{icon} [{log['timestamp']}] {log['agent']}</strong>
                        <div style="color: #C9D1D9; font-size: 0.75rem; margin-top: 3px; line-height: 1.3;">{log['message']}</div>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

        if st.session_state.get("completed_logs_mobile") and st.session_state.get("latest_report"):
            report_content = st.session_state.latest_report
            if report_content != "아직 생성된 보고서가 없습니다.":
                st.markdown("##### 📄 최신 업무 브리핑 보고서 (Result)")
                st.markdown(f"<div class='report-card'>{report_content}</div>", unsafe_allow_html=True)

    with tab_report:
        st.markdown("##### 📄 최신 업무 브리핑")
        
        latest_report_content = "아직 생성된 보고서가 없습니다."
        try:
            log_files = sorted(glob.glob("logs/report_*.txt"), reverse=True)
            if log_files:
                with open(log_files[0], "r", encoding="utf-8") as f:
                    latest_report_content = f.read()
        except Exception as e:
            latest_report_content = f"보고서 로드 실패: {e}"
            
        report_to_show = st.session_state.get("latest_report", latest_report_content)
        st.markdown(f"<div class='report-card'>{report_to_show}</div>", unsafe_allow_html=True)

    with tab_archive:
        st.markdown("##### 🗄️ 아카이브 보고서")
        try:
            log_files = sorted(glob.glob("logs/report_*.txt"), reverse=True)
            if log_files:
                selected_log = st.selectbox("보고서 선택", log_files, format_func=lambda x: os.path.basename(x))
                with open(selected_log, "r", encoding="utf-8") as f:
                    content = f.read()
                st.markdown(f"<div class='report-card'>{content}</div>", unsafe_allow_html=True)
            else:
                st.info("아직 생성된 보고서가 없습니다.")
        except Exception as e:
            st.error(f"보고서 로드 실패: {e}")

# --- Routing Logic ---
is_mobile = st.query_params.get("device") == "mobile"

if is_mobile:
    render_mobile_ui()
else:
    render_desktop_ui()
