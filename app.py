import streamlit as st
import pandas as pd
from datetime import date, timedelta

st.set_page_config(
    page_title="AI Student Planner",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 AI Student Planner")
st.write("Интеллектуальный планировщик учебных заданий")

st.sidebar.title("Навигация")

page = st.sidebar.radio(
    "Выберите раздел",
    ["Главная", "Мои задания", "AI-анализ", "Расписание"]
)

if "tasks" not in st.session_state:
    st.session_state.tasks = []

if page == "Главная":
    st.header("Панель управления")
    st.info("Добро пожаловать в AI Student Planner!")

    col1, col2, col3 = st.columns(3)

    col1.metric("Всего заданий", len(st.session_state.tasks))
    col2.metric("Выполнено", sum(t["done"] for t in st.session_state.tasks))
    col3.metric("Осталось", sum(not t["done"] for t in st.session_state.tasks))

elif page == "Мои задания":
    st.header("Добавление задания")

    with st.form("task_form"):
        name = st.text_input("Название задания")
        subject = st.text_input("Предмет")
        deadline = st.date_input("Срок сдачи", date.today() + timedelta(days=3))
        difficulty = st.slider("Сложность", 1, 5, 3)
        hours = st.number_input("Время выполнения (часы)", 0.5, 20.0, 2.0)

        submitted = st.form_submit_button("Добавить задание")

        if submitted and name:
            st.session_state.tasks.append({
                "name": name,
                "subject": subject,
                "deadline": deadline,
                "difficulty": difficulty,
                "hours": hours,
                "done": False
            })
            st.success("Задание добавлено!")

    if st.session_state.tasks:
        st.dataframe(pd.DataFrame(st.session_state.tasks), use_container_width=True)

elif page == "AI-анализ":
    st.header("AI-анализ заданий")
    st.info("Здесь будет интеллектуальный анализ заданий.")

elif page == "Расписание":
    st.header("Учебное расписание")
    st.info("Здесь будет автоматически созданное расписание.")
