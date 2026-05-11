import streamlit as st
import pandas as pd
import sqlite3
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

# 加载环境变量
load_dotenv()
DOUBAO_API_KEY = os.getenv("DOUBAO_API_KEY")

# 初始化数据库
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # 用户表
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  role TEXT NOT NULL)''')
    
    # 学案表
    c.execute('''CREATE TABLE IF NOT EXISTS learning_plans
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  subject TEXT NOT NULL,
                  grade TEXT NOT NULL,
                  content TEXT NOT NULL,
                  teacher_id INTEGER,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # 练习题表
    c.execute('''CREATE TABLE IF NOT EXISTS exercises
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  plan_id INTEGER,
                  question TEXT NOT NULL,
                  options TEXT,
                  answer TEXT NOT NULL,
                  difficulty INTEGER DEFAULT 2)''')
    
    # 学生答题记录表
    c.execute('''CREATE TABLE IF NOT EXISTS student_answers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  student_id INTEGER,
                  exercise_id INTEGER,
                  student_answer TEXT,
                  is_correct BOOLEAN,
                  answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    conn.close()

# 用户认证
def login(username, password):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, role FROM users WHERE username=? AND password=?", (username, password))
    user = c.fetchone()
    conn.close()
    return user

def register(username, password, role):
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  (username, password, role))
        conn.commit()
        conn.close()
        return True
    except:
        return False

# 调用豆包API
def call_doubao(prompt):
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    headers = {
        "Authorization": f"Bearer {DOUBAO_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "py test_api.py",  
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return "AI服务暂时不可用"

# 主函数
def main():
    st.set_page_config(page_title="中学个性化学案系统", layout="wide")
    st.title("📚 中学个性化学案系统")
    
    # 初始化数据库
    init_db()
    
    # 会话状态
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
        st.session_state.role = None
    
    # 侧边栏登录/注册
    with st.sidebar:
        if st.session_state.user_id is None:
            st.subheader("登录/注册")
            tab1, tab2 = st.tabs(["登录", "注册"])
            
            with tab1:
                username = st.text_input("用户名")
                password = st.text_input("密码", type="password")
                if st.button("登录"):
                    user = login(username, password)
                    if user:
                        st.session_state.user_id = user[0]
                        st.session_state.role = user[1]
                        st.success("登录成功！")
                        st.rerun()
                    else:
                        st.error("用户名或密码错误")
            
            with tab2:
                new_username = st.text_input("新用户名")
                new_password = st.text_input("新密码", type="password")
                role = st.selectbox("角色", ["学生", "教师"])
                if st.button("注册"):
                    if register(new_username, new_password, role):
                        st.success("注册成功，请登录")
                    else:
                        st.error("用户名已存在")
        else:
            st.write(f"欢迎，{st.session_state.role}")
            if st.button("退出登录"):
                st.session_state.user_id = None
                st.session_state.role = None
                st.rerun()
    
    # 根据角色显示不同页面
    if st.session_state.user_id is not None:
        if st.session_state.role == "教师":
            teacher_page()
        else:
            student_page()

# 教师页面
def teacher_page():
    st.subheader("👨‍🏫 教师工作台")
    menu = st.sidebar.selectbox("功能菜单", ["创建学案", "我的学案", "学情分析"])
    
    if menu == "创建学案":
        create_learning_plan()
    elif menu == "我的学案":
        view_my_plans()
    elif menu == "学情分析":
        view_learning_analytics()

# 学生页面
def student_page():
    st.subheader("👨‍🎓 学生学习中心")
    menu = st.sidebar.selectbox("功能菜单", ["我的学案", "错题本", "学习报告"])
    
    if menu == "我的学案":
        view_assigned_plans()
    elif menu == "错题本":
        view_mistakes()
    elif menu == "学习报告":
        view_student_report()

# 教师：创建学案（升级版，带AI辅助）
def create_learning_plan():
    st.subheader("创建新学案")
    
    title = st.text_input("学案标题")
    subject = st.selectbox("学科", ["语文", "数学", "英语", "物理", "化学"])
    grade = st.selectbox("年级", ["七年级", "八年级", "九年级", "高一", "高二", "高三"])
    
    # AI辅助生成内容
    if st.button("AI帮我生成学案内容"):
        prompt = f"""
        请为{grade}{subject}学科生成一份关于"{title}"的学案内容，包括：
        1. 学习目标
        2. 重点难点
        3. 知识点讲解
        4. 典型例题
        """
        with st.spinner("AI正在生成学案内容..."):
            ai_content = call_doubao(prompt)
            st.session_state.ai_content = ai_content
    
    content = st.text_area("学案内容", value=st.session_state.get('ai_content', ''), height=200)
    
    st.subheader("添加练习题")
    num_questions = st.number_input("题目数量", min_value=1, max_value=20, value=5)
    
    # AI辅助生成练习题
    if st.button("AI帮我生成练习题"):
        prompt = f"""
        请为{grade}{subject}学科"{title}"这节课生成{num_questions}道单选题，难度适中。
        输出格式：
        1. 题目1
        A. 选项A
        B. 选项B
        C. 选项C
        D. 选项D
        答案：X
        
        2. 题目2
        ...
        """
        with st.spinner("AI正在生成练习题..."):
            ai_questions = call_doubao(prompt)
            st.session_state.ai_questions = ai_questions
            st.write(ai_questions)
    
    questions = []
    for i in range(num_questions):
        st.write(f"**第{i+1}题**")
        q_type = st.selectbox(f"题型{i+1}", ["单选题", "判断题"], key=f"type_{i}")
        question = st.text_area(f"题目内容{i+1}", key=f"q_{i}")
        
        if q_type == "单选题":
            options = st.text_input(f"选项（用逗号分隔，如：A.选项1,B.选项2）", key=f"opt_{i}")
        else:
            options = "正确,错误"
        
        answer = st.text_input(f"正确答案（如：A 或 正确）", key=f"ans_{i}")
        difficulty = st.slider(f"难度", 1, 5, 2, key=f"diff_{i}")
        
        questions.append({
            "question": question,
            "options": options,
            "answer": answer,
            "difficulty": difficulty
        })
    
    if st.button("保存学案"):
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        c.execute("INSERT INTO learning_plans (title, subject, grade, content, teacher_id) VALUES (?, ?, ?, ?, ?)",
                  (title, subject, grade, content, st.session_state.user_id))
        plan_id = c.lastrowid
        
        for q in questions:
            c.execute("INSERT INTO exercises (plan_id, question, options, answer, difficulty) VALUES (?, ?, ?, ?, ?)",
                      (plan_id, q["question"], q["options"], q["answer"], q["difficulty"]))
        
        conn.commit()
        conn.close()
        st.success("学案创建成功！")

# 教师：查看我的学案
def view_my_plans():
    st.subheader("我的学案")
    
    conn = sqlite3.connect('database.db')
    df = pd.read_sql_query("SELECT * FROM learning_plans WHERE teacher_id=?", conn, params=(st.session_state.user_id,))
    conn.close()
    
    if df.empty:
        st.info("你还没有创建任何学案")
        return
    
    for _, row in df.iterrows():
        with st.expander(f"{row['title']} - {row['subject']} {row['grade']}"):
            st.write(row['content'])
            st.write("**练习题：**")
            
            conn = sqlite3.connect('database.db')
            exercises = pd.read_sql_query("SELECT * FROM exercises WHERE plan_id=?", conn, params=(row['id'],))
            conn.close()
            
            for i, ex in exercises.iterrows():
                st.write(f"{i+1}. {ex['question']}")
                if ex['options']:
                    options = ex['options'].split(',')
                    for opt in options:
                        st.write(opt)
                st.write(f"**答案：{ex['answer']}**")

# 学生：查看分配的学案
def view_assigned_plans():
    st.subheader("我的学案")
    
    conn = sqlite3.connect('database.db')
    # 这里简化处理，显示所有学案，实际可以添加班级分配功能
    df = pd.read_sql_query("SELECT * FROM learning_plans", conn)
    conn.close()
    
    if df.empty:
        st.info("暂时没有可用的学案")
        return
    
    selected_plan = st.selectbox("选择学案", df['title'].tolist())
    plan = df[df['title'] == selected_plan].iloc[0]
    
    st.subheader(plan['title'])
    st.write(plan['content'])
    
    st.subheader("练习题")
    conn = sqlite3.connect('database.db')
    exercises = pd.read_sql_query("SELECT * FROM exercises WHERE plan_id=?", conn, params=(plan['id'],))
    conn.close()
    
    student_answers = {}
    for i, ex in exercises.iterrows():
        st.write(f"**{i+1}. {ex['question']}**")
        options = ex['options'].split(',')
        student_answers[ex['id']] = st.radio(f"选择你的答案", options, key=f"ans_{ex['id']}")
    
    if st.button("提交答案"):
        score = 0
        total = len(exercises)
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        for i, ex in exercises.iterrows():
            student_ans = student_answers[ex['id']]
            is_correct = student_ans == ex['answer']
            
            if is_correct:
                score += 1
            
            c.execute("INSERT INTO student_answers (student_id, exercise_id, student_answer, is_correct) VALUES (?, ?, ?, ?)",
                      (st.session_state.user_id, ex['id'], student_ans, is_correct))
        
        conn.commit()
        conn.close()
        
        st.success(f"提交成功！你的得分：{score}/{total}")
        
        if score < total:
            st.info("做错的题目已经自动加入你的错题本")

# 学生：查看错题本（升级版，带AI解析）
def view_mistakes():
    st.subheader("我的错题本")
    
    conn = sqlite3.connect('database.db')
    df = pd.read_sql_query("""
        SELECT e.id, e.question, e.options, e.answer, sa.student_answer, sa.answered_at
        FROM student_answers sa
        JOIN exercises e ON sa.exercise_id = e.id
        WHERE sa.student_id=? AND sa.is_correct=0
        ORDER BY sa.answered_at DESC
    """, conn, params=(st.session_state.user_id,))
    conn.close()
    
    if df.empty:
        st.info("太棒了！你还没有错题")
        return
    
    for i, row in df.iterrows():
        with st.expander(f"错题{i+1} - {row['answered_at']}"):
            st.write(f"**题目：** {row['question']}")
            if row['options']:
                options = row['options'].split(',')
                for opt in options:
                    st.write(opt)
            st.write(f"**你的答案：** {row['student_answer']}")
            st.write(f"**正确答案：** {row['answer']}")
            
            if st.button("AI解析", key=f"ai_{row['id']}"):
                prompt = f"""
                请为下面这道中学题目写一个详细的解析：
                题目：{row['question']}
                选项：{row['options']}
                正确答案：{row['answer']}
                学生错误答案：{row['student_answer']}
                
                解析需要包括：
                1. 本题考查的知识点
                2. 详细的解题过程
                3. 学生错误的原因分析
                4. 同类题目的解题技巧
                """
                with st.spinner("AI正在生成解析..."):
                    explanation = call_doubao(prompt)
                    st.write("**AI解析：**")
                    st.write(explanation)
            
            if st.button("生成同类题", key=f"similar_{row['id']}"):
                prompt = f"""
                请根据下面这道题生成3道难度相近的同类练习题：
                题目：{row['question']}
                选项：{row['options']}
                正确答案：{row['answer']}
                
                输出格式：
                1. 题目1
                A. 选项A
                B. 选项B
                C. 选项C
                D. 选项D
                答案：X
                
                2. 题目2
                ...
                """
                with st.spinner("AI正在生成同类题..."):
                    similar_questions = call_doubao(prompt)
                    st.write("**同类练习题：**")
                    st.write(similar_questions)

# 教师：学情分析
def view_learning_analytics():
    st.subheader("学情分析")
    st.info("该功能正在开发中，后续更新")

# 学生：学习报告
def view_student_report():
    st.subheader("学习报告")
    st.info("该功能正在开发中，后续更新")

if __name__ == "__main__":
    main()
    