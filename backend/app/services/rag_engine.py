from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser

from app.core.config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    CHROMA_DB_PATH,
    RAG_CHUNK_SIZE,
    RAG_CHUNK_OVERLAP,
    RAG_RETRIEVER_K
)

# Verify OpenAI API key is set
if not OPENAI_API_KEY:
    raise ValueError(
        "OPENAI_API_KEY not found in environment variables. "
        "Please add it to your .env file: OPENAI_API_KEY=your-key-here"
    )

class HealthRAGEngine:
    def __init__(self, knowledge_base_path: str):
        """Initialize RAG engine with knowledge base documents"""
        
        # Read knowledge base
        with open(knowledge_base_path, 'r') as f:
            self.knowledge_text = f.read()
        
        # Split text into chunks (important for retrieval)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=RAG_CHUNK_SIZE,
            chunk_overlap=RAG_CHUNK_OVERLAP
        )
        chunks = self.text_splitter.split_text(self.knowledge_text)
        
        # Create vector store (Chroma stores embeddings locally)
        self.embeddings = OpenAIEmbeddings()
        self.vectorstore = Chroma.from_texts(
            chunks,
            self.embeddings,
            persist_directory=CHROMA_DB_PATH
        )
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": RAG_RETRIEVER_K})
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model_name=OPENAI_MODEL,
            temperature=OPENAI_TEMPERATURE
        )
    
    def format_docs(self, docs):
        """Format retrieved documents for LLM"""
        return "\n\n".join(doc.page_content for doc in docs)
    
    def generate_health_insight(self, user_data: dict) -> dict:
        """
        Generate evidence-backed health insights based on user data and knowledge base.
        
        Args:
            user_data: {
                'age': int,
                'symptoms': [str],
                'labs': {'lab_name': value},
                'wearables': {'metric': value}
            }
        
        Returns:
            {
                'assessment': str,
                'top_dysfunctions': [str],
                'interventions': [dict],
                'evidence_sources': [str]
            }
        """
        
        # Format user data into a question for RAG
        query = f"""
        Patient Summary:
        - Age: {user_data.get('age', 'unknown')}
        - Symptoms: {', '.join(user_data.get('symptoms', []))}
        - Lab Results: {user_data.get('labs', {})}
        - Wearable Data: {user_data.get('wearables', {})}
        
        Based on functional medicine principles, what are the likely dysfunctions 
        and evidence-based interventions?
        """
        
        # Build RAG chain
        rag_chain = (
            {"context": self.retriever | self.format_docs, "question": RunnablePassthrough()}
            | ChatPromptTemplate.from_template("""You are a functional medicine AI assistant. 
            Use the following context from medical protocols to answer the question.
            
            Context: {context}
            
            Question: {question}
            
            Provide:
            1. Top 3 suspected dysfunctions with severity (mild/moderate/severe)
            2. Evidence-based interventions for each
            3. Key citations from the knowledge base
            
            Format as JSON.""")
            | self.llm
            | StrOutputParser()
        )
        
        response = rag_chain.invoke(query)
        return {"response": response, "user_data": user_data}

# Example usage
if __name__ == "__main__":
    from app.core.config import KNOWLEDGE_BASE_PATH
    engine = HealthRAGEngine(KNOWLEDGE_BASE_PATH)
    
    user_data = {
        'age': 35,
        'symptoms': ['fatigue', 'poor sleep', 'brain fog'],
        'labs': {'fasting_glucose': 105, 'cortisol_morning': 18},
        'wearables': {'sleep_hours': 5.5, 'hrv': 35}
    }
    
    insight = engine.generate_health_insight(user_data)
    print(insight['response'])
