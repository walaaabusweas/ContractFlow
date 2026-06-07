from graphs.state_schema import AgentState
from utils.decorators import track_tokens

@track_tokens("language_detector_node")
def language_detector_node(state: AgentState) -> AgentState:
    """
    Detect the contract language from extracted text and store it in state.contract_language.
    """
    print("--- [NODE] DETECTING CONTRACT LANGUAGE ---")

    text = state.contract_text or ""
    if not text.strip():
        state.update({"contract_language": "unknown"})
        print("⚠️ No contract text found for language detection.")
        return state

    letters = [char for char in text if char.isalpha()]
    if not letters:
        state.update({"contract_language": "unknown"})
        print("⚠️ No alphabetic text found for language detection.")
        return state

    arabic_letters = [
        char for char in letters
        if "\u0600" <= char <= "\u06ff" or "\u0750" <= char <= "\u077f" or "\u08a0" <= char <= "\u08ff"
    ]
    arabic_ratio = len(arabic_letters) / len(letters)
    language = "ar" if arabic_ratio >= 0.25 else "en"

    state.update({"contract_language": language})
    print(f"✅ Contract language detected: {language}")
    return state
