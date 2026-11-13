import json
from datetime import date, timedelta
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.ensemble import RandomForestClassifier

st.set_page_config(page_title='AI Student Planner 2.0', page_icon='🎓', layout='wide')
DATA = Path(__file__).with_name('tasks.json')
st.markdown('''<style> .stApp{background:#10131d;color:#e8edf8} [data-testid="stSidebar"]{background:#171d2b} div[data-testid="stMetric"]{background:#1c2942;padding:18px;border-radius:16px;border:1px solid #34435d} h1,h2,h3{color:#f2f5ff} .stButton>button[kind="primary"]{background:#6574ed;border:0;border-radius:10px} </style>''', unsafe_allow_html=True)

def load():
    if not DATA.exists(): return []
    try:
        value=json.loads(DATA.read_text(encoding='utf-8'))
        return value if isinstance(value,list) else []
    except (OSError,ValueError): return []

def save():
    DATA.write_text(json.dumps(st.session_state.tasks,ensure_ascii=False,indent=2),encoding='utf-8')

if 'tasks' not in st.session_state: st.session_state.tasks=load()

def days_left(t): return (date.fromisoformat(t['deadline'])-date.today()).days

def features(t): return [max(-10,min(90,days_left(t))),int(t['difficulty']),float(t['hours'])]

@st.cache_resource
def get_model():
    rng=np.random.default_rng(42)
    days=rng.integers(-5,61,1800)
    diff=rng.integers(1,6,1800)
    hours=rng.uniform(.5,15,1800)
    urgency=np.where(days<=0,55,np.where(days<=2,45,np.where(days<=7,30,np.where(days<=14,15,0))))
    scores=urgency+diff*7+np.minimum(hours,12)*2
    labels=np.where(scores>=73,2,np.where(scores>=47,1,0))
    X=np.column_stack((days,diff,hours))
    model=RandomForestClassifier(n_estimators=120,max_depth=9,random_state=42)
    model.fit(X,labels)
    return model

MODEL=get_model()
LEVEL={0:'🟢 Низкий',1:'🟠 Средний',2:'🔴 Высокий'}

def priority(t):
    label=int(MODEL.predict([features(t)])[0])
    days=days_left(t)
    if days<0: label=2
    return label

def pending(): return [t for t in st.session_state.tasks if not t.get('done',False)]

def ranked(): return sorted(pending(),key=lambda t:(-priority(t),days_left(t),-int(t['difficulty'])))

st.sidebar.title('🎓 AI Planner')
page=st.sidebar.radio('Навигация',['🏠 Главная','📚 Мои задания','🧠 AI-анализ','🗓️ Расписание','ℹ️ О проекте'])
st.sidebar.caption('Данные сохраняются в tasks.json на сервере приложения. На бесплатном облачном хостинге они могут исчезнуть при перезапуске.')

if page=='🏠 Главная':
    st.title('🎓 AI Student Planner 2.0')
    st.caption('Планируй задачи, оценивай приоритеты и распределяй время')
    tasks=st.session_state.tasks
    done=sum(bool(t.get('done')) for t in tasks)
    cols=st.columns(4)
    for col,label,value in zip(cols,['Всего заданий','Выполнено','Осталось','Прогресс'],[len(tasks),done,len(tasks)-done,f'{done/len(tasks)*100:.0f}%' if tasks else '0%']): col.metric(label,value)
    st.progress(done/len(tasks) if tasks else 0)
    st.subheader('Что делать в первую очередь')
    for t in ranked()[:5]:
        d=days_left(t)
        st.info(f"{LEVEL[priority(t)]} · **{t['name']}** ({t['subject']}) · {('просрочено на '+str(-d)+' дн.') if d<0 else ('осталось '+str(d)+' дн.')} · {t['hours']} ч")
    if not pending(): st.success('Добавь первое задание или все задачи уже выполнены!')

elif page=='📚 Мои задания':
    st.title('📚 Мои задания')
    with st.form('add',clear_on_submit=True):
        name=st.text_input('Название задания')
        subject=st.text_input('Предмет')
        deadline=st.date_input('Дедлайн',value=date.today()+timedelta(days=3))
        difficulty=st.slider('Сложность',1,5,3)
        hours=st.number_input('Необходимое время (часы)',min_value=.5,max_value=100.,value=2.,step=.5)
        if st.form_submit_button('➕ Добавить задание',type='primary'):
            if not name.strip() or not subject.strip(): st.error('Заполни название и предмет.')
            else:
                import uuid
                st.session_state.tasks.append(dict(id=str(uuid.uuid4()),name=name.strip(),subject=subject.strip(),deadline=deadline.isoformat(),difficulty=difficulty,hours=float(hours),done=False))
                save();st.rerun()
    st.divider()
    for t in list(st.session_state.tasks):
        with st.expander(('✅ ' if t.get('done') else '📌 ')+t['name']+' · '+t['subject']):
            with st.form('edit_'+t['id']):
                n=st.text_input('Название',value=t['name'])
                s=st.text_input('Предмет',value=t['subject'])
                d=st.date_input('Дедлайн',value=date.fromisoformat(t['deadline']))
                dif=st.slider('Сложность',1,5,int(t['difficulty']))
                h=st.number_input('Часы',min_value=.5,max_value=100.,value=float(t['hours']),step=.5)
                done=st.checkbox('Выполнено',value=bool(t.get('done')))
                c1,c2=st.columns(2)
                update=c1.form_submit_button('💾 Сохранить')
                delete=c2.form_submit_button('🗑️ Удалить')
                if update:
                    if n.strip() and s.strip():
                        t.update(name=n.strip(),subject=s.strip(),deadline=d.isoformat(),difficulty=dif,hours=float(h),done=done)
                        save();st.rerun()
                    else: st.error('Название и предмет обязательны.')
                if delete:
                    st.session_state.tasks=[x for x in st.session_state.tasks if x['id']!=t['id']]
                    save();st.rerun()

elif page=='🧠 AI-анализ':
    st.title('🧠 Анализ приоритетов')
    st.info('Модель RandomForestClassifier обучена на синтетических учебных примерах по правилам срочности, сложности и трудоёмкости. Это демонстрационный ML-прототип, а не проверенная модель на реальных студенческих данных.')
    tasks=ranked()
    if tasks:
        rows=[]
        for t in tasks:
            rows.append({'Задание':t['name'],'Предмет':t['subject'],'Дедлайн':t['deadline'],'Дней осталось':days_left(t),'Сложность':t['difficulty'],'Часы':t['hours'],'Приоритет':LEVEL[priority(t)]})
        df=pd.DataFrame(rows)
        st.dataframe(df,use_container_width=True,hide_index=True)
        st.subheader('Количество задач по приоритетам')
        st.bar_chart(df['Приоритет'].value_counts())
        first=tasks[0]
        st.success(f"Рекомендуем начать с «{first['name']}» ({first['subject']}): приоритет {LEVEL[priority(first)]}, срок {first['deadline']}, примерно {first['hours']} ч.")
    else: st.info('Добавь хотя бы одно невыполненное задание.')

elif page=='🗓️ Расписание':
    st.title('🗓️ Умное расписание')
    per_day=st.slider('Сколько часов в день готов учиться?',1,12,3)
    horizon=st.slider('На сколько дней составить план?',1,30,14)
    tasks=ranked()
    remaining={t['id']:float(t['hours']) for t in tasks}
    rows=[]
    for offset in range(horizon):
        current=date.today()+timedelta(days=offset)
        capacity=float(per_day)
        for t in tasks:
            if capacity<=.001: break
            if remaining[t['id']]<=.001: continue
            if date.fromisoformat(t['deadline'])<current and days_left(t)>=0: continue
            amount=min(capacity,remaining[t['id']])
            rows.append({'Дата':current.isoformat(),'Задание':t['name'],'Предмет':t['subject'],'Часов':round(amount,2),'Дедлайн':t['deadline']})
            remaining[t['id']]-=amount
            capacity-=amount
    if rows:
        df=pd.DataFrame(rows)
        st.dataframe(df,use_container_width=True,hide_index=True)
        st.bar_chart(df.groupby('Дата')['Часов'].sum())
        st.download_button('⬇️ Скачать расписание CSV',df.to_csv(index=False).encode('utf-8-sig'),'schedule.csv','text/csv')
    else: st.info('Добавь задания для создания расписания.')
    unplanned=[t['name'] for t in tasks if remaining[t['id']]>.001]
    if unplanned: st.warning('Не удалось полностью распределить в выбранном периоде: '+', '.join(unplanned)+'. Увеличь количество часов или период планирования.')
    st.caption('Алгоритм распределяет задачи по приоритету и дедлайну. Это эвристический планировщик, не оптимизационная нейросеть.')
