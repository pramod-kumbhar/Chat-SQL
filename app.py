import streamlit as st
from pathlib import Path
from langchain_community.utilities import SQLDatabase
from langchain.callbacks.streamlit import StreamlitCallbackHandler
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.agent_toolkits import create_sql_agent
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from langchain.agents import AgentType
import sqlite3
from langchain_groq import ChatGroq

st.set_page_config(page_title="LangChain: Chat with SQL DB",page_icon='🦜')
st.title("🦜Langchain:Chat with SQL DB")

INJECTION_WARNING="""
                   SQL agent can be vulnerable to prompt injection. Use a DB role with limited permissions.
                   Read more[here](https://python.langchain.com/docs/security)."""

LOCALDB="USE_LOCALDB"
MYSQL="USE_MYSQL"

radio_opt=["USe SQLlited 3 Database - Student.db",'Connect to you SQL Database']

selected_opt=st.sidebar.radio(label="Choose the DB which you want to chat",options=radio_opt)

# if radio_opt.index(selected_opt)==1:
#     db_uri=MYSQL
#     mysql_host=st.sidebar.text_input('Provide My SQL host')
#     mysql_port = st.sidebar.text_input("Port")
#     mysql_user=st.sidebar.text_input('MYSQL user')
#     mysql_password=st.sidebar.text_input('MYSQL password',type='password')
#     mysql_db=st.sidebar.text_input('MySQL database')
# else:
#     db_uri=LOCALDB  
    
if selected_opt == radio_opt[1]:
    db_uri = MYSQL
    mysql_host = st.sidebar.text_input("Host", value="127.0.0.1")
    mysql_port = st.sidebar.text_input("Port", value="3306")
    mysql_user = st.sidebar.text_input("MySQL User")
    mysql_password = st.sidebar.text_input("MySQL Password", type="password")
    mysql_db = st.sidebar.text_input("Database Name")
else:
    db_uri = LOCALDB     
    
api_key=st.sidebar.text_input(label='GROQ API KEY',type="password")
# api_key=""

if not db_uri:
    st.info('Please enter ther databse information and uri')
    
if not api_key:
    st.info('Please add the groq api key') 
    st.stop()
 
    
## LLM model
llm=ChatGroq(groq_api_key=api_key,model_name="llama-3.1-8b-instant",streaming=True)

# @st.cache_resource(ttl="2h")
# def configure_db(db_uri,mysql_host=None,mysql_user=None,mysql_password=None,mysql_db=None):
#     if db_uri==LOCALDB:
#         dbfilepath=(Path(__file__).parent/'student.db').absolute()
#         print(dbfilepath)     
#         creator=lambda:sqlite3.connect(f"file:{dbfilepath}?mode=ro",uri=True)
#         return SQLDatabase(create_engine("sqlite:///",creator=creator)) 
#     elif db_uri==MYSQL:
#         if not all ([mysql_host, mysql_user, mysql_password, mysql_db]):
#             st.error("Please provide all MySQL connection details.")
#             st.stop()
            
#         url = URL.create(
#             drivername="mysql+mysqlconnector",
#             username=mysql_user,
#             password=mysql_password,
#             host=mysql_host,
#             # port=int(mysql_port),
#             database=mysql_db
#         )

#         engine = create_engine(url)
#         return SQLDatabase(engine)

@st.cache_resource(ttl="2h")
def configure_db(db_uri, mysql_host=None, mysql_port=3306,
                 mysql_user=None, mysql_password=None, mysql_db=None):

    if db_uri == LOCALDB:
        dbfilepath = (Path(__file__).parent / 'student.db').absolute()

        def creator():
            return sqlite3.connect(f"file:{dbfilepath}?mode=ro", uri=True)

        engine = create_engine("sqlite://", creator=creator)
        return SQLDatabase(engine)

    elif db_uri == MYSQL:

        if not all([mysql_host, mysql_port, mysql_user, mysql_password, mysql_db]):
            st.error("Missing MySQL credentials")
            st.stop()

        url = URL.create(
            drivername="mysql+mysqlconnector",
            username=mysql_user,
            password=mysql_password,
            host=mysql_host,
            port=int(mysql_port),
            database=mysql_db
        )

        engine = create_engine(url)
        return SQLDatabase(engine)
    
# if db_uri == MYSQL:
#     db = configure_db(
#     db_uri=db_uri,
#     mysql_host=mysql_host,
#     # mysql_port=mysql_port,
#     mysql_user=mysql_user,
#     mysql_password=mysql_password,
#     mysql_db=mysql_db
# )
# else:
#     db = configure_db(db_uri)

if db_uri == MYSQL:    
    db = configure_db(
        db_uri=db_uri,
        mysql_host=mysql_host,
        mysql_port=mysql_port,
        mysql_user=mysql_user,
        mysql_password=mysql_password,
        mysql_db=mysql_db
    ) 
else:
    db = configure_db(db_uri)       
    
    
### toolkit
toolkit=SQLDatabaseToolkit(db=db,llm=llm)

agent=create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    verbose=True,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    handle_parsing_errors=True
)       
 
if 'messages' not in st.session_state or st.sidebar.button('Clear messade history'):
    st.session_state['messages']=[{'role':'assistant','content':'how can i help you?'}] 
       
       
for msg in st.session_state.messages:
    st.chat_message(msg['role']).write(msg['content'])
    
user_query=st.chat_input(placeholder='Ask anything from the databse')

if user_query:
    st.session_state.messages.append({'role':'user','content':user_query})    
    
    with st.chat_message('assistant'):
        streamlit_callback=StreamlitCallbackHandler(st.container())
        response=agent.invoke({'input':user_query},{'callbacks':[streamlit_callback]})
        st.session_state.messages.append({'role':'assistant','content':response})
        st.write(response['output'])
           