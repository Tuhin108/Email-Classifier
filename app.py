import streamlit as st
import google.generativeai as genai
import json
import re
from datetime import datetime
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
CONVERSATION_FILE = "email_classification_history.json"

# Configure the page
st.set_page_config(
    page_title="Email Spam Classifier",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        margin-bottom: 30px;
    }
    .spam-result {
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
        text-align: center;
        font-size: 18px;
        font-weight: bold;
    }
    .spam {
        background-color: #ffebee;
        border: 2px solid #f44336;
        color: #d32f2f;
    }
    .not-spam {
        background-color: #e8f5e8;
        border: 2px solid #4caf50;
        color: #388e3c;
    }
    .confidence-bar {
        background-color: #f0f0f0;
        border-radius: 10px;
        padding: 3px;
        margin: 10px 0;
    }
    .confidence-fill {
        height: 20px;
        border-radius: 7px;
        text-align: center;
        line-height: 20px;
        color: white;
        font-weight: bold;
    }
    .stats-container {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)

class SpamClassifier:
    def __init__(self, api_key):
        """Initialize the spam classifier with Gemini API"""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
    def create_prompt(self, email_content):
        """Create a structured prompt for spam classification"""
        prompt = f"""
        You are an expert email spam classifier. Analyze the following email content and determine if it's spam or not spam.

        Email Content:
        "{email_content}"

        Please analyze this email based on the following criteria:
        1. Suspicious sender patterns
        2. Urgency and pressure tactics
        3. Financial offers or requests
        4. Suspicious links or attachments mentions
        5. Grammar and spelling quality
        6. Legitimate business communication patterns

        Provide your response in the following JSON format:
        {{
            "classification": "spam" or "not_spam",
            "confidence_score": [0-100],
            "reasoning": "Brief explanation of your decision",
            "spam_indicators": ["list", "of", "specific", "indicators", "found"],
            "risk_level": "low", "medium", or "high"
        }}

        Be thorough but concise in your analysis.
        """
        return prompt
    
    def classify_email(self, email_content):
        """Classify email using Gemini API"""
        try:
            prompt = self.create_prompt(email_content)
            response = self.model.generate_content(prompt)
            
            # Extract JSON from response
            response_text = response.text
            
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                return result
            else:
                # Fallback parsing if JSON is not properly formatted
                return self._fallback_parse(response_text)
                
        except Exception as e:
            st.error(f"Error in classification: {str(e)}")
            return None
    
    def _fallback_parse(self, response_text):
        """Fallback parsing method if JSON extraction fails"""
        # Basic fallback - look for key indicators in the response
        response_lower = response_text.lower()
        
        if "spam" in response_lower and "not spam" not in response_lower:
            classification = "spam"
        else:
            classification = "not_spam"
            
        return {
            "classification": classification,
            "confidence_score": 75,
            "reasoning": "Analyzed based on content patterns",
            "spam_indicators": ["Analysis completed"],
            "risk_level": "medium"
        }

def initialize_session_state():
    """Initialize session state variables"""
    if 'classification_history' not in st.session_state:
        st.session_state.classification_history = load_conversation_history()
    if 'total_emails' not in st.session_state:
        st.session_state.total_emails = len(st.session_state.classification_history)
    if 'spam_count' not in st.session_state:
        st.session_state.spam_count = sum(1 for entry in st.session_state.classification_history 
                                         if entry['result']['classification'] == 'spam')

def load_conversation_history():
    """Load conversation history from JSON file"""
    try:
        if os.path.exists(CONVERSATION_FILE):
            with open(CONVERSATION_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return []
    except Exception as e:
        st.error(f"Error loading conversation history: {str(e)}")
        return []

def save_conversation_history(history):
    """Save conversation history to JSON file"""
    try:
        with open(CONVERSATION_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        st.error(f"Error saving conversation history: {str(e)}")

def add_to_history(email_content, result):
    """Add a new classification to history and save to file"""
    new_entry = {
        'id': len(st.session_state.classification_history) + 1,
        'timestamp': datetime.now().isoformat(),
        'email_content': email_content,
        'content_preview': email_content[:100] + "..." if len(email_content) > 100 else email_content,
        'result': result,
        'session_info': {
            'user_agent': 'Streamlit App',
            'classification_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    }
    
    st.session_state.classification_history.append(new_entry)
    save_conversation_history(st.session_state.classification_history)
    
    # Update counters
    st.session_state.total_emails = len(st.session_state.classification_history)
    st.session_state.spam_count = sum(1 for entry in st.session_state.classification_history 
                                     if entry['result']['classification'] == 'spam')

def display_result(result):
    """Display classification result with styling"""
    if result:
        classification = result['classification']
        confidence = result['confidence_score']
        reasoning = result['reasoning']
        indicators = result.get('spam_indicators', [])
        risk_level = result.get('risk_level', 'medium')
        
        # Display main result
        if classification == "spam":
            st.markdown(f"""
            <div class="spam-result spam">
                🚨 SPAM DETECTED 🚨<br>
                Risk Level: {risk_level.upper()}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="spam-result not-spam">
                ✅ LEGITIMATE EMAIL ✅<br>
                Risk Level: {risk_level.upper()}
            </div>
            """, unsafe_allow_html=True)
        
        # Confidence bar
        color = "#f44336" if classification == "spam" else "#4caf50"
        st.markdown(f"""
        <div class="confidence-bar">
            <div class="confidence-fill" style="width: {confidence}%; background-color: {color};">
                Confidence: {confidence}%
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Detailed analysis
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔍 Analysis Reasoning")
            st.write(reasoning)
        
        with col2:
            st.subheader("⚠️ Identified Indicators")
            for indicator in indicators:
                st.write(f"• {indicator}")

def display_statistics():
    """Display classification statistics"""
    if st.session_state.total_emails > 0:
        spam_percentage = (st.session_state.spam_count / st.session_state.total_emails) * 100
        legitimate_percentage = 100 - spam_percentage
        
        st.markdown("""
        <div class="stats-container">
            <h3>📊 Classification Statistics</h3>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Emails Analyzed", st.session_state.total_emails)
        
        with col2:
            st.metric("Spam Detected", st.session_state.spam_count, 
                     f"{spam_percentage:.1f}%")
        
        with col3:
            st.metric("Legitimate Emails", 
                     st.session_state.total_emails - st.session_state.spam_count,
                     f"{legitimate_percentage:.1f}%")

def main():
    """Main Streamlit application"""
    initialize_session_state()
    
    # Header
    st.markdown('<h1 class="main-header">📧 AI Email Spam Classifier</h1>', 
                unsafe_allow_html=True)
    st.markdown("---")
    
    # Get API key from environment
    api_key = os.getenv("GEMINI_API_KEY")
    
    # Sidebar for information
    with st.sidebar:
        st.header("🔧 Configuration")
        if api_key:
            st.success("✅ API Key loaded from environment")
        else:
            st.error("❌ API Key not found in environment")
            st.warning("Please set GEMINI_API_KEY in your .env file")
        
        st.markdown("---")
        st.header("📊 Data Management")
        
        # Export history
        if st.button("📥 Export History"):
            if st.session_state.classification_history:
                json_data = json.dumps(st.session_state.classification_history, indent=2, ensure_ascii=False)
                st.download_button(
                    label="💾 Download JSON",
                    data=json_data,
                    file_name=f"email_classifications_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            else:
                st.info("No classification history to export")
        
        # Clear history
        if st.button("🗑️ Clear History"):
            if st.session_state.classification_history:
                if st.checkbox("⚠️ Confirm deletion"):
                    st.session_state.classification_history = []
                    st.session_state.total_emails = 0
                    st.session_state.spam_count = 0
                    save_conversation_history([])
                    st.success("History cleared!")
                    st.rerun()
            else:
                st.info("No history to clear")
        
        # Show file status
        if os.path.exists(CONVERSATION_FILE):
            file_size = os.path.getsize(CONVERSATION_FILE)
            st.info(f"📁 History file: {file_size} bytes")
        
        st.markdown("---")
        st.header("🔗 Get API Key")
        st.write("[Google AI Studio](https://makersuite.google.com/app/apikey)")
        
        st.markdown("---")
        st.header("⚙️ Setup")
        st.code("""
# Create .env file with:
GEMINI_API_KEY=your_api_key_here
        """, language="bash")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📝 Email Content Input")
        email_content = st.text_area(
            "Paste the email content here:",
            height=300,
            placeholder="""Example:
Subject: Urgent: Your Account Will Be Suspended

Dear Customer,

Your account will be suspended in 24 hours due to suspicious activity. 
Click here immediately to verify your account: [suspicious-link.com]

Provide your username, password, and credit card details to avoid suspension.

Act now or lose access forever!

Best regards,
Security Team"""
        )
        
        # Classification button and results
    st.markdown("---")
    
    if st.button("🔍 Classify Email", type="primary", use_container_width=True):
        if not api_key:
            st.error("⚠️ Please set your GEMINI_API_KEY in the .env file!")
            st.info("Create a .env file in your project directory with: GEMINI_API_KEY=your_api_key_here")
        elif not email_content.strip():
            st.error("⚠️ Please enter email content to analyze!")
        else:
            with st.spinner("🤖 Analyzing email with AI..."):
                classifier = SpamClassifier(api_key)
                result = classifier.classify_email(email_content)
                
                if result:
                    # Add to history and save to JSON
                    add_to_history(email_content, result)
                    
                    # Display result
                    display_result(result)
                    
                    # Update statistics
                    st.rerun()
    
    # Classification history
    if st.session_state.classification_history:
        st.markdown("---")
        st.subheader("📚 Recent Classifications")
        
        # Show last 5 classifications
        for i, entry in enumerate(reversed(st.session_state.classification_history[-5:])):
            with st.expander(f"#{entry['id']} - {entry['session_info']['classification_time']} - {entry['result']['classification'].replace('_', ' ').title()}"):
                st.write(f"**Content Preview:** {entry['content_preview']}")
                st.write(f"**Classification:** {entry['result']['classification']}")
                st.write(f"**Confidence:** {entry['result']['confidence_score']}%")
                st.write(f"**Risk Level:** {entry['result']['risk_level']}")
                st.write(f"**Reasoning:** {entry['result']['reasoning']}")
                
                # Show full email content
                st.write("**📧 Full Email Content:**")
                st.text_area("", value=entry['email_content'], height=150, disabled=True, key=f"email_{entry['id']}", label_visibility="collapsed")
    
    # File information
    st.markdown("---")
    st.info(f"💾 All classifications are automatically saved to: `{CONVERSATION_FILE}`")

if __name__ == "__main__":
    main()