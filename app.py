import json
import math
import os
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="AI Student Planner", page_icon="🎓", layout="wide")
DATA_FILE = Path(os.getenv("PLANNER_DATA_FILE", "tasks.json"))


def load_tasks():
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError, TypeError):
        return []


def save_tasks():
    try:
        DATA_FILE.write_text(json.dumps(st.session_state.tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except OSError as exc:
        st.error(f"Не удалось сохранить данные: {exc}")
        return False


if "tasks" not in st.session_state:
    st.session_state.tasks = load_tasks()


def priority(task):
    days = (date.fromisoformat(task["deadline"]) - date.today()).days
    urgency = 60 if days < 0 else 50 if days == 0 else 40 if days == 1 else 30 if days <= 3 else 20 if days <= 7 else 10
    score = urgency + int(task["difficulty"]) * 6 + min(float(task["hours"]), 12) * 1.5
    return round(min(score, 100), 1)


def priority_label(score):
    return "🔴 Высокий" if score >= 65 else "🟠 Средний" if score >= 40 else "🟢 Низкий"


def task_table(tasks):
    rows = []
    for t in tasks:
        rows.append({"Задание": t["name"], "Предмет": t["subject"], "Дедлайн": t["deadline"],
                     "Сложность": t["difficulty"], "Часы": t["hours"],
                     "Приоритет": priority_label(priority(t)), "Баллы": priority(t)})
    return pd.DataFrame(rows)


def schedule(tasks, hours_per_day, horizon):
    pending = sorted((t for t in tasks if not t["done"]),
                     key=lambda t: (-priority(t), t["deadline"]))
    remaining = {t["id"]: float(t["hours"]) for t in pending}
    result = []
    for offset in range(horizon):
        current = date.today() + timedelta(days=offset)
        available = hours_per_day
        for task in pending:
            if available <= 0:
                break
            if remaining[task["id"]] <= 0:
                continue
            if current > date.fromisoformat(task["deadline"]):
                continue
            assigned = round(min(remaining[task["id"]], available), 2)
            if assigned > 0:
                result.append({"Дата": current.isoformat(), "Задание": task["name"],
                               "Предмет": task["subject"], "Часов": assigned,
                               "Дедлайн": task["deadline"]})
                remaining[task["id"]] -= assigned
                available -= assigned
    unscheduled = [(t, round(remaining[t["id"]], 2)) for t in pending if remaining[t["id"]] > 0.001]
    return result, unscheduled


st.markdown("""<style>
.block-container {padding-top: 2rem; max-width: 1250px;}
[data-testid="stMetric"] {background: #18243a; padding: 18px; border-radius: 14px;}
[data-testid="stMetricLabel"] {color: #cbd5e1;}
h1, h2, h3 {letter-spacing: -.02em;}
</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🎓 AI Planner")
    page = st.radio("Навигация", ["🏠 Главная", "📚 Мои задания", "🧠 AI-анализ", "📅 Расписание"])
    st.caption("Умное планирование учёбы")

all_tasks = st.session_state.tasks
pending = [t for t in all_tasks if not t["done"]]
completed = len(all_tasks) - len(pending)

if page == "🏠 Главная":
    st.title("🎓 AI Student Planner")
    st.caption("Планируй задачи, оценивай приоритеты и распределяй время")
    a, b, c, d = st.columns(4)
    a.metric("Всего заданий", len(all_tasks))
    b.metric("Выполнено", completed)
    c.metric("Осталось", len(pending))
    d.metric("Прогресс", f"{completed / len(all_tasks):.0%}" if all_tasks else "0%")
    st.progress(completed / len(all_tasks) if all_tasks else 0)
    st.subheader("Что делать в первую очередь")
    if pending:
        top = sorted(pending, key=lambda t: (-priority(t), t["deadline"]))[:5]
        st.dataframe(task_table(top), hide_index=True, use_container_width=True)
    else:
        st.info("Добавь первое задание в разделе «Мои задания».")

elif page == "📚 Мои задания":
    st.title("📚 Мои задания")
    with st.form("new_task", clear_on_submit=True):
        st.subheader("Добавить задание")
        name = st.text_input("Название задания")
        subject = st.text_input("Предмет")
        deadline = st.date_input("Срок сдачи", value=date.today() + timedelta(days=3))
        difficulty = st.slider("Сложность", 1, 5, 3)
        hours = st.number_input("Время выполнения (часы)", min_value=0.5, max_value=100.0, value=2.0, step=0.5)
        submitted = st.form_submit_button("➕ Добавить задание", type="primary")
        if submitted:
            if not name.strip() or not subject.strip():
                st.warning("Заполни название задания и предмет.")
            else:
                all_tasks.append({"id": str(uuid.uuid4()), "name": name.strip(), "subject": subject.strip(),
                                  "deadline": deadline.isoformat(), "difficulty": difficulty,
                                  "hours": float(hours), "done": False})
                save_tasks()
                st.rerun()
    st.subheader("Список заданий")
    if not all_tasks:
        st.info("Пока заданий нет.")
    for t in list(all_tasks):
        col1, col2, col3 = st.columns([6, 2, 1])
        with col1:
            st.write(f"**{t['name']}** · {t['subject']} · до {t['deadline']} · {t['hours']} ч")
            st.caption(f"{priority_label(priority(t))} · сложность {t['difficulty']}/5")
        with col2:
            done = st.checkbox("Выполнено", value=t["done"], key=f"done_{t['id']}")
            if done != t["done"]:
                t["done"] = done
                save_tasks()
                st.rerun()
        with col3:
            if st.button("🗑️", key=f"del_{t['id']}", help="Удалить задание"):
                all_tasks.remove(t)
                save_tasks()
                st.rerun()
        st.divider()

elif page == "🧠 AI-анализ":
    st.title("🧠 Анализ приоритетов")
    st.info("Приоритет рассчитывается по понятным правилам: близость дедлайна, сложность и время выполнения. Это алгоритм, а не обученная нейросеть.")
    if pending:
        ranked = sorted(pending, key=lambda t: (-priority(t), t["deadline"]))
        st.dataframe(task_table(ranked), hide_index=True, use_container_width=True)
        st.subheader("Рекомендация")
        first = ranked[0]
        days = (date.fromisoformat(first["deadline"]) - date.today()).days
        when = "срок уже прошёл" if days < 0 else "сегодня" if days == 0 else f"через {days} дн."
        st.success(f"Начни с «{first['name']}» ({first['subject']}): дедлайн {when}, сложность {first['difficulty']}/5, потребуется около {first['hours']} ч.")
        st.bar_chart(pd.DataFrame({"Задание": [t["name"] for t in ranked],
                                   "Приоритет": [priority(t) for t in ranked]}).set_index("Задание"))
    else:
        st.info("Добавь незавершённые задания для анализа.")

elif page == "📅 Расписание":
    st.title("📅 Умное расписание")
    hours_per_day = st.slider("Сколько часов в день готов учиться?", 1, 12, 3)
    horizon = st.slider("План на сколько дней?", 3, 30, 14)
    if pending:
        rows, unscheduled = schedule(pending, hours_per_day, horizon)
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, hide_index=True, use_container_width=True)
            st.bar_chart(df.groupby("Дата")["Часов"].sum())
            st.download_button("📥 Скачать расписание CSV", df.to_csv(index=False).encode("utf-8-sig"),
                               file_name="student_schedule.csv", mime="text/csv")
        else:
            st.warning("Не удалось распределить задания до их дедлайнов.")
        if unscheduled:
            st.warning("Не хватает времени до дедлайнов или в выбранном периоде для некоторых заданий:")
            for t, hours_left in unscheduled:
                st.write(f"• {t['name']}: осталось {hours_left} ч (до {t['deadline']})")
    else:
        st.info("Добавь задания, чтобы составить расписание.")
    st.caption("План формируется по приоритету и свободным часам. Он не учитывает конкретные часы занятий и выходные.")
