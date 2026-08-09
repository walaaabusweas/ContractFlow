def get_language_instruction(lang_code):
    if lang_code == "ar":
        return "All extracted values MUST be in ARABIC. Do not use any other language."
    elif lang_code == "en":
        return "All extracted values MUST be in ENGLISH. Do not use any other language."
    return "Use the language of the source document for all extracted values."