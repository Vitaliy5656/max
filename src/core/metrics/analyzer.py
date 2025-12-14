"""
Implicit Feedback Analyzer Module.

Detects positive, negative, and correction signals in user messages.
"""


class ImplicitFeedbackAnalyzer:
    """Detects implicit positive/negative signals in user messages."""
    
    POSITIVE_SIGNALS = [
        # Благодарность и одобрение
        "спасибо", "благодарю", "благодарствую",
        "отлично", "превосходно", "замечательно", "великолепно", "прекрасно",
        "супер", "класс", "круто", "кайф", "огонь", "топ",
        "молодец", "молодчина", "умница",
        "хорошо", "неплохо", "нормально",
        "это то что надо", "то что нужно", "именно так",
        "да, это", "точно", "верно", "правильно", "абсолютно",
        "согласен", "согласна", "соглашусь",
        "понял", "понятно", "ясно", "разобрался",
        "именно", "в точку", "попал",
        "годится", "подходит", "устраивает", "сойдет",
        "работает", "получилось", "заработало", "решено",
        "ага", "угу", "окей", "ок", "лады", "гуд",
        
        # English
        "thanks", "thank you", "thx", "ty",
        "great", "awesome", "excellent", "perfect", "amazing", "wonderful",
        "nice", "good", "cool", "neat",
        "good job", "well done", "nicely done",
        "exactly", "precisely", "correct", "right",
        "yes", "yeah", "yep", "yup",
        "got it", "understood", "makes sense",
        "works", "working", "solved", "fixed"
    ]
    
    NEGATIVE_SIGNALS = [
        # Отрицание и несогласие
        "нет", "не то", "не так", "не совсем", "не совсем то",
        "неправильно", "ошибка", "неверно", "неточно",
        "ты ошибся", "ты ошибаешься", "ошибешься",
        "это неправда", "неправда",
        "плохо", "ужасно", "отвратительно", "кошмар",
        "не понимаешь", "не понял", "не поняла",
        "опять", "снова", "заново", "переделай", "исправь",
        "бред", "чушь", "ерунда", "глупость", "фигня",
        "не надо", "не нужно", "убери", "удали",
        "хватит", "достаточно", "прекрати", "стоп",
        "я же сказал", "я уже говорил", "повторяю",
        "ты издеваешься", "ты прикалываешься",
        "при чём тут", "не об этом", "не про это",
        "мимо", "промахнулся",
        "забудь", "неважно", "проехали",
        
        # Переспрашивание / непонимание
        "я имел в виду", "я имела в виду",
        "ты не понял", "ты не поняла",
        "другое", "другой", "иначе",
        
        # English
        "no", "nope", "wrong", "incorrect", "not right",
        "error", "mistake", "fail",
        "bad", "terrible", "awful",
        "not what i", "that's not", "this is not",
        "i meant", "i said", "i asked",
        "again", "redo", "retry", "fix",
        "stop", "enough", "nevermind", "forget it"
    ]
    
    CORRECTION_SIGNALS = [
        # Русские паттерны коррекции
        "нет, я имел в виду",
        "нет, я имела в виду",
        "нет, имелось в виду",
        "не так, я хотел",
        "не так, я хотела",
        "ты не понял",
        "ты не поняла",
        "ты меня не понял",
        "я хотел сказать",
        "я хотела сказать",
        "имелось в виду",
        "другое, я про",
        "не то что я просил",
        "не то что я просила",
        "я просил другое",
        "я просила другое",
        "перечитай мой вопрос",
        "перечитай что я написал",
        "я же написал",
        "я же сказал",
        "не это, а",
        "совсем не то",
        "вообще не то",
        "абсолютно не то",
        "нет-нет-нет",
        "стоп, не так",
        "подожди, не то",
        "слушай внимательнее",
        "читай внимательнее",
        
        # English correction patterns
        "no, i meant",
        "no i meant",
        "that's not what i",
        "thats not what i",
        "not what i asked",
        "not what i meant",
        "i was asking about",
        "i meant something else",
        "reread my question",
        "read again",
        "you misunderstood",
        "you got it wrong",
        "let me rephrase",
        "let me clarify"
    ]
    
    # Words that indicate emphasis (important) when in caps, not frustration
    EMPHASIS_CONTEXT = [
        "важно", "внимание", "срочно", "обязательно", "критично",
        "запомни", "учти", "никогда", "всегда", "только",
        "именно", "ключевое", "главное", "основное",
        "important", "urgent", "critical", "never", "always", "must",
        "note", "remember", "key", "main", "only"
    ]
    
    # Minimum caps ratio to consider it significant (avoid short words)
    MIN_CAPS_RATIO = 0.5
    MIN_CAPS_LENGTH = 3  # Minimum word length to analyze for caps
    
    def analyze(self, text: str) -> tuple[bool, bool, bool]:
        """
        Analyze text for implicit feedback signals.
        
        Returns:
            tuple: (is_positive, is_negative, is_correction)
        """
        text_lower = text.lower()
        
        is_positive = any(sig in text_lower for sig in self.POSITIVE_SIGNALS)
        is_negative = any(sig in text_lower for sig in self.NEGATIVE_SIGNALS)
        is_correction = any(sig in text_lower for sig in self.CORRECTION_SIGNALS)
        
        # Correction overrides simple negative
        if is_correction:
            is_negative = True
        
        # CAPS detection with context
        caps_analysis = self._analyze_caps(text, is_negative)
        if caps_analysis == "frustration":
            is_negative = True
        elif caps_analysis == "emphasis" and not is_negative:
            # Emphasis is neutral, not negative
            pass
        
        return is_positive, is_negative, is_correction
    
    def _analyze_caps(self, text: str, already_negative: bool) -> str:
        """
        Analyze CAPS usage in text to determine intent.
        
        Returns:
            "frustration" - angry caps (negative signal)
            "emphasis" - important emphasis (neutral)
            "none" - no significant caps
        """
        # Find all caps words (3+ chars)
        words = text.split()
        caps_words = []
        
        for word in words:
            # Remove punctuation for analysis
            clean = ''.join(c for c in word if c.isalpha())
            if len(clean) >= self.MIN_CAPS_LENGTH:
                upper_count = sum(1 for c in clean if c.isupper())
                ratio = upper_count / len(clean)
                if ratio >= self.MIN_CAPS_RATIO:
                    caps_words.append(clean)
        
        if not caps_words:
            return "none"
        
        # Calculate overall caps presence
        total_alpha = sum(1 for c in text if c.isalpha())
        total_upper = sum(1 for c in text if c.isupper())
        
        if total_alpha == 0:
            return "none"
        
        caps_ratio = total_upper / total_alpha
        
        # If less than 20% caps overall, probably not significant
        if caps_ratio < 0.2:
            return "none"
        
        # Check context: is it emphasis or frustration?
        text_lower = text.lower()
        
        # Check for emphasis context
        is_emphasis = any(ctx in text_lower for ctx in self.EMPHASIS_CONTEXT)
        
        # Check for frustration signals
        frustration_signals = [
            "!!!", "?!",  # Multiple punctuation
            "блин", "черт", "damn", "hell",  # Mild swearing
            "сколько раз", "я же", "опять",  # Repetition frustration
            "почему ты не", "зачем ты",  # Questioning actions
        ]
        has_frustration = any(sig in text_lower for sig in frustration_signals)
        
        # Decision logic
        if has_frustration or already_negative:
            # CAPS + frustration signals = definitely frustrated
            return "frustration"
        elif is_emphasis:
            # CAPS + emphasis words = just highlighting importance
            return "emphasis"
        elif caps_ratio > 0.7:
            # Very high caps ratio with no context = likely frustration
            return "frustration"
        else:
            # Default to emphasis if unclear
            return "emphasis"
    
    def get_caps_info(self, text: str) -> dict:
        """
        Get detailed caps analysis for debugging/UI.
        
        Returns dict with caps ratio, interpretation, etc.
        """
        total_alpha = sum(1 for c in text if c.isalpha())
        total_upper = sum(1 for c in text if c.isupper())
        
        caps_ratio = total_upper / total_alpha if total_alpha > 0 else 0
        interpretation = self._analyze_caps(text, False)
        
        return {
            "caps_ratio": round(caps_ratio, 2),
            "interpretation": interpretation,
            "significant": caps_ratio >= 0.2
        }
