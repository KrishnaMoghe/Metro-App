"""Public-announcement templates in English, Hindi and Gujarati."""

TEMPLATES = {
    "pre_arrival": {
        "en": "Welcome to {station} station. Passengers for {event}, please exit through {gate} and follow the green signs. Please buy your return QR ticket now to avoid queues after the event.",
        "hi": "{station} स्टेशन पर आपका स्वागत है। {event} के लिए आने वाले यात्री कृपया {gate} से बाहर निकलें और हरे संकेतों का पालन करें। कार्यक्रम के बाद कतार से बचने के लिए अभी अपना वापसी QR टिकट खरीद लें।",
        "gu": "{station} સ્ટેશન પર આપનું સ્વાગત છે. {event} માટે આવતા મુસાફરો કૃપા કરીને {gate} થી બહાર નીકળો અને લીલા સંકેતોને અનુસરો. કાર્યક્રમ પછી લાઈન ટાળવા માટે અત્યારે જ તમારી રિટર્ન QR ટિકિટ ખરીદી લો.",
    },
    "gate_open": {
        "en": "Attention please. {gate} is now open for entry. Passengers are requested to use {gate} and keep moving in a single line.",
        "hi": "कृपया ध्यान दें। {gate} अब प्रवेश के लिए खुला है। यात्रियों से अनुरोध है कि {gate} का उपयोग करें और एक कतार में आगे बढ़ें।",
        "gu": "કૃપા કરીને ધ્યાન આપો. {gate} હવે પ્રવેશ માટે ખુલ્લો છે. મુસાફરોને વિનંતી છે કે {gate} નો ઉપયોગ કરો અને એક લાઈનમાં આગળ વધો.",
    },
    "holding": {
        "en": "Dear passengers, the station is at full capacity. Please wait at {holding}. You will be allowed in batches. The next train will arrive in {minutes} minutes. Thank you for your patience.",
        "hi": "प्रिय यात्रियों, स्टेशन पूरी क्षमता पर है। कृपया {holding} पर प्रतीक्षा करें। आपको समूहों में प्रवेश दिया जाएगा। अगली ट्रेन {minutes} मिनट में आएगी। धैर्य रखने के लिए धन्यवाद।",
        "gu": "પ્રિય મુસાફરો, સ્ટેશન સંપૂર્ણ ક્ષમતા પર છે. કૃપા કરીને {holding} પર રાહ જુઓ. તમને જૂથમાં પ્રવેશ આપવામાં આવશે. આગામી ટ્રેન {minutes} મિનિટમાં આવશે. ધીરજ રાખવા બદલ આભાર.",
    },
    "train_added": {
        "en": "Special announcement. Additional trains are running from {station} every {minutes} minutes. Please do not rush; there is space for everyone.",
        "hi": "विशेष सूचना। {station} से हर {minutes} मिनट में अतिरिक्त ट्रेनें चल रही हैं। कृपया धक्का-मुक्की न करें, सभी के लिए जगह है।",
        "gu": "વિશેષ જાહેરાત. {station} થી દર {minutes} મિનિટે વધારાની ટ્રેનો દોડી રહી છે. કૃપા કરીને ધક્કામુક્કી ન કરો, દરેક માટે જગ્યા છે.",
    },
    "platform_full": {
        "en": "Platform is crowded. Please stay behind the yellow line, let passengers alight first, and wait for the next train arriving in {minutes} minutes.",
        "hi": "प्लेटफॉर्म पर भीड़ है। कृपया पीली रेखा के पीछे रहें, पहले यात्रियों को उतरने दें और {minutes} मिनट में आने वाली अगली ट्रेन की प्रतीक्षा करें।",
        "gu": "પ્લેટફોર્મ પર ભીડ છે. કૃપા કરીને પીળી રેખાની પાછળ રહો, પહેલા મુસાફરોને ઉતરવા દો અને {minutes} મિનિટમાં આવનારી આગામી ટ્રેનની રાહ જુઓ.",
    },
    "release": {
        "en": "Crowd levels are now normal at {station}. Holding areas are closed and all passengers may proceed directly to the gates. Thank you for travelling with Ahmedabad Metro.",
        "hi": "{station} पर भीड़ अब सामान्य है। होल्डिंग क्षेत्र बंद कर दिए गए हैं और सभी यात्री सीधे गेट की ओर जा सकते हैं। अहमदाबाद मेट्रो से यात्रा करने के लिए धन्यवाद।",
        "gu": "{station} પર ભીડ હવે સામાન્ય છે. હોલ્ડિંગ વિસ્તારો બંધ કરવામાં આવ્યા છે અને બધા મુસાફરો સીધા ગેટ તરફ જઈ શકે છે. અમદાવાદ મેટ્રોમાં મુસાફરી કરવા બદલ આભાર.",
    },
}

TITLES = {
    "pre_arrival": "Pre-event arrival guidance", "gate_open": "Gate opening", "holding": "Holding area / batching",
    "train_added": "Extra trains running", "platform_full": "Platform crowding", "release": "All clear",
}


def render(key, **kw):
    t = TEMPLATES[key]
    return {"key": key, "title": TITLES[key], **{lang: t[lang].format(**kw) for lang in ("en", "hi", "gu")}}
