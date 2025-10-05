# services/hindu_calendar.py - Hindu Calendar Integration for Religious Content
import calendar
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

class HinduMonth(Enum):
    CHAITRA = ("chaitra", "चैत्र", 1)
    VAISHAKHA = ("vaishakha", "वैशाख", 2)
    JYAISTHA = ("jyaistha", "ज्येष्ठ", 3)
    ASHADHA = ("ashadha", "आषाढ़", 4)
    SHRAVANA = ("shravana", "श्रावण", 5)
    BHADRAPADA = ("bhadrapada", "भाद्रपद", 6)
    ASHVINA = ("ashvina", "आश्विन", 7)
    KARTIKA = ("kartika", "कार्तिक", 8)
    AGRAHAYANA = ("agrahayana", "अग्रहायण", 9)
    PAUSHA = ("pausha", "पौष", 10)
    MAGHA = ("magha", "माघ", 11)
    PHALGUNA = ("phalguna", "फाल्गुन", 12)

class Nakshatra(Enum):
    ASHWINI = ("ashwini", "अश्विनी")
    BHARANI = ("bharani", "भरणी")
    KRITTIKA = ("krittika", "कृत्तिका")
    ROHINI = ("rohini", "रोहिणी")
    MRIGASHIRA = ("mrigashira", "मृगशिरा")
    ARDRA = ("ardra", "आर्द्रा")
    PUNARVASU = ("punarvasu", "पुनर्वसु")
    PUSHYA = ("pushya", "पुष्य")
    ASHLESHA = ("ashlesha", "आश्लेषा")
    MAGHA = ("magha", "मघा")
    PURVA_PHALGUNI = ("purva_phalguni", "पूर्वा फाल्गुनी")
    UTTARA_PHALGUNI = ("uttara_phalguni", "उत्तरा फाल्गुनी")
    HASTA = ("hasta", "हस्त")
    CHITRA = ("chitra", "चित्रा")
    SWATI = ("swati", "स्वाती")
    VISHAKHA = ("vishakha", "विशाखा")
    ANURADHA = ("anuradha", "अनुराधा")
    JYESHTHA = ("jyeshtha", "ज्येष्ठा")
    MULA = ("mula", "मूल")
    PURVA_ASHADHA = ("purva_ashadha", "पूर्वाषाढ़ा")
    UTTARA_ASHADHA = ("uttara_ashadha", "उत्तराषाढ़ा")
    SHRAVANA_NAKSHATRA = ("shravana", "श्रवण")
    DHANISHTHA = ("dhanishtha", "धनिष्ठा")
    SHATABHISHA = ("shatabhisha", "शतभिषा")
    PURVA_BHADRAPADA = ("purva_bhadrapada", "पूर्वाभाद्रपदा")
    UTTARA_BHADRAPADA = ("uttara_bhadrapada", "उत्तराभाद्रपदा")
    REVATI = ("revati", "रेवती")

class Yoga(Enum):
    VISHKUMBHA = ("vishkumbha", "विष्कुम्भ")
    PREETI = ("preeti", "प्रीति")
    AYUSHMAN = ("ayushman", "आयुष्मान")
    SAUBHAGYA = ("saubhagya", "सौभाग्य")
    SHOBHANA = ("shobhana", "शोभन")
    ATIGANDA = ("atiganda", "अतिगण्ड")
    SUKARMA = ("sukarma", "सुकर्म")
    DHRITI = ("dhriti", "धृति")
    SHULA = ("shula", "शूल")
    GANDA = ("ganda", "गण्ड")
    VRIDDHI = ("vriddhi", "वृद्धि")
    DHRUVA = ("dhruva", "ध्रुव")
    VYAGHATA = ("vyaghata", "व्याघात")
    HARSHANA = ("harshana", "हर्षण")
    VAJRA = ("vajra", "वज्र")
    SIDDHI = ("siddhi", "सिद्धि")
    VYATIPATA = ("vyatipata", "व्यतीपात")
    VARIYANA = ("variyana", "वरीयान")
    PARIGHA = ("parigha", "परिघ")
    SHIVA = ("shiva", "शिव")
    SIDDHA = ("siddha", "सिद्ध")
    SADHYA = ("sadhya", "साध्य")
    SHUBHA = ("shubha", "शुभ")
    SHUKLA = ("shukla", "शुक्ल")
    BRAHMA = ("brahma", "ब्रह्म")
    INDRA = ("indra", "इन्द्र")
    VAIDHRITI = ("vaidhriti", "वैधृति")

class Karana(Enum):
    BAVA = ("bava", "बव")
    BALAVA = ("balava", "बालव")
    KAULAVA = ("kaulava", "कौलव")
    TAITILA = ("taitila", "तैतिल")
    GARA = ("gara", "गर")
    VANIJA = ("vanija", "वणिज")
    VISHTI = ("vishti", "विष्टि")
    SHAKUNI = ("shakuni", "शकुनि")
    CHATUSHPADA = ("chatushpada", "चतुष्पद")
    NAGA = ("naga", "नाग")
    KIMSTUGHNA = ("kimstughna", "किंस्तुघ्न")

class HinduFestival:
    def __init__(self, name: str, hindi_name: str, month: HinduMonth, 
                 day: int, description: str, significance: str, 
                 rituals: List[str] = None, is_major: bool = False):
        self.name = name
        self.hindi_name = hindi_name
        self.month = month
        self.day = day
        self.description = description
        self.significance = significance
        self.rituals = rituals or []
        self.is_major = is_major

class HinduCalendarService:
    """Service for Hindu calendar calculations and festival dates"""
    
    def __init__(self):
        self.festivals = self._initialize_festivals()
        self.nakshatras = list(Nakshatra)
        self.yogas = list(Yoga)
        self.karanas = list(Karana)
    
    def _initialize_festivals(self) -> List[HinduFestival]:
        """Initialize major Hindu festivals"""
        return [
            HinduFestival(
                "Makar Sankranti", "मकर संक्रांति", HinduMonth.PAUSHA, 14,
                "Harvest festival marking the sun's transition to Capricorn",
                "Marks the end of winter solstice and beginning of longer days",
                ["Kite flying", "Tilgul distribution", "Holy bath"], True
            ),
            HinduFestival(
                "Vasant Panchami", "वसंत पंचमी", HinduMonth.MAGHA, 5,
                "Festival celebrating the arrival of spring and honoring Goddess Saraswati",
                "Worship of knowledge, arts, and wisdom",
                ["Saraswati Puja", "Yellow color celebration", "Kite flying"], True
            ),
            HinduFestival(
                "Maha Shivratri", "महा शिवरात्रि", HinduMonth.PHALGUNA, 13,
                "Great night of Lord Shiva worship",
                "Most auspicious night for Shiva devotees",
                ["All-night vigil", "Rudra Abhishek", "Fasting"], True
            ),
            HinduFestival(
                "Holi", "होली", HinduMonth.PHALGUNA, 15,
                "Festival of colors celebrating the victory of good over evil",
                "Celebrates divine love and the arrival of spring",
                ["Color throwing", "Holika Dahan", "Community celebration"], True
            ),
            HinduFestival(
                "Ram Navami", "राम नवमी", HinduMonth.CHAITRA, 9,
                "Birth anniversary of Lord Rama",
                "Celebrates the birth of Maryada Purushottam Rama",
                ["Ramayana recitation", "Jhankis", "Community feasts"], True
            ),
            HinduFestival(
                "Hanuman Jayanti", "हनुमान जयंती", HinduMonth.CHAITRA, 15,
                "Birth anniversary of Lord Hanuman",
                "Celebrates devotion, strength, and courage",
                ["Hanuman Chalisa", "Strength demonstrations", "Temple visits"], True
            ),
            HinduFestival(
                "Akshaya Tritiya", "अक्षय तृतीया", HinduMonth.VAISHAKHA, 3,
                "Auspicious day for new beginnings",
                "Day of eternal prosperity and good fortune",
                ["Gold purchases", "New ventures", "Charity"], True
            ),
            HinduFestival(
                "Buddha Purnima", "बुद्ध पूर्णिमा", HinduMonth.VAISHAKHA, 15,
                "Birth anniversary of Lord Buddha",
                "Celebrates enlightenment and compassion",
                ["Meditation", "Bodhi tree worship", "Acts of kindness"], True
            ),
            HinduFestival(
                "Rath Yatra", "रथ यात्रा", HinduMonth.ASHADHA, 2,
                "Chariot festival of Lord Jagannath",
                "Divine journey of Lord Jagannath",
                ["Chariot procession", "Community participation", "Prasad distribution"], True
            ),
            HinduFestival(
                "Guru Purnima", "गुरु पूर्णिमा", HinduMonth.ASHADHA, 15,
                "Day to honor spiritual teachers and gurus",
                "Celebrates the guru-disciple tradition",
                ["Guru worship", "Dakshina offering", "Knowledge sharing"], True
            ),
            HinduFestival(
                "Raksha Bandhan", "रक्षा बंधन", HinduMonth.SHRAVANA, 15,
                "Festival celebrating brother-sister bond",
                "Symbol of protection and love between siblings",
                ["Rakhi tying", "Gift exchange", "Family gatherings"], True
            ),
            HinduFestival(
                "Krishna Janmashtami", "कृष्ण जन्माष्टमी", HinduMonth.BHADRAPADA, 8,
                "Birth anniversary of Lord Krishna",
                "Celebrates divine love and playfulness",
                ["Midnight celebration", "Dahi Handi", "Bhajan singing"], True
            ),
            HinduFestival(
                "Ganesh Chaturthi", "गणेश चतुर्थी", HinduMonth.BHADRAPADA, 4,
                "Birth anniversary of Lord Ganesha",
                "Celebrates wisdom and remover of obstacles",
                ["Ganpati installation", "Modak offering", "Visarjan"], True
            ),
            HinduFestival(
                "Navratri", "नवरात्रि", HinduMonth.ASHVINA, 1,
                "Nine nights celebrating Goddess Durga",
                "Victory of good over evil through divine feminine power",
                ["Durga Puja", "Garba dance", "Fasting", "Kanya Pujan"], True
            ),
            HinduFestival(
                "Dussehra", "दशहरा", HinduMonth.ASHVINA, 10,
                "Victory of Lord Rama over Ravana",
                "Triumph of righteousness over evil",
                ["Ravana effigy burning", "Ram Lila", "Weapon worship"], True
            ),
            HinduFestival(
                "Karva Chauth", "करवा चौथ", HinduMonth.KARTIKA, 4,
                "Fasting for husband's long life",
                "Symbol of married women's devotion",
                ["Moon worship", "Mehendi", "Sargi"], True
            ),
            HinduFestival(
                "Diwali", "दिवाली", HinduMonth.KARTIKA, 15,
                "Festival of lights celebrating the return of Lord Rama",
                "Victory of light over darkness",
                ["Lakshmi Puja", "Rangoli", "Fireworks", "Sweet distribution"], True
            ),
            HinduFestival(
                "Bhai Dooj", "भाई दूज", HinduMonth.KARTIKA, 2,
                "Festival celebrating brother-sister love",
                "Sisters pray for brothers' well-being",
                ["Tilaka ceremony", "Aarti", "Gift exchange"], True
            ),
        ]
    
    def get_festivals_for_month(self, month: int, year: int) -> List[Dict]:
        """Get festivals for a specific month"""
        # This is a simplified version - in production, you'd calculate actual lunar dates
        gregorian_to_hindu_month = {
            1: HinduMonth.PAUSHA, 2: HinduMonth.MAGHA, 3: HinduMonth.PHALGUNA,
            4: HinduMonth.CHAITRA, 5: HinduMonth.VAISHAKHA, 6: HinduMonth.JYAISTHA,
            7: HinduMonth.ASHADHA, 8: HinduMonth.SHRAVANA, 9: HinduMonth.BHADRAPADA,
            10: HinduMonth.ASHVINA, 11: HinduMonth.KARTIKA, 12: HinduMonth.AGRAHAYANA
        }
        
        hindu_month = gregorian_to_hindu_month.get(month)
        if not hindu_month:
            return []
        
        festivals = [f for f in self.festivals if f.month == hindu_month]
        
        result = []
        for festival in festivals:
            # Approximate date calculation (in production, use proper lunar calendar)
            approx_date = date(year, month, min(festival.day, calendar.monthrange(year, month)[1]))
            result.append({
                "name": festival.name,
                "hindi_name": festival.hindi_name,
                "date": approx_date.isoformat(),
                "description": festival.description,
                "significance": festival.significance,
                "rituals": festival.rituals,
                "is_major": festival.is_major
            })
        
        return result
    
    def get_festivals_for_year(self, year: int) -> Dict[int, List[Dict]]:
        """Get all festivals for a year organized by month"""
        result = {}
        for month in range(1, 13):
            festivals = self.get_festivals_for_month(month, year)
            if festivals:
                result[month] = festivals
        return result
    
    def generate_daily_panchang(self, target_date: date) -> Dict:
        """Generate panchang for a specific date"""
        # This is a simplified version - in production, use proper astronomical calculations
        
        # Calculate indices based on date (simplified approximation)
        day_of_year = target_date.timetuple().tm_yday
        
        nakshatra_index = (day_of_year + 7) % len(self.nakshatras)
        yoga_index = (day_of_year + 3) % len(self.yogas)
        karana_index = (day_of_year * 2 + 5) % len(self.karanas)
        
        # Calculate tithi (simplified)
        lunar_day = (day_of_year % 30) + 1
        paksha = "शुक्ल पक्ष" if lunar_day <= 15 else "कृष्ण पक्ष"
        tithi_names = [
            "प्रतिपदा", "द्वितीया", "तृतीया", "चतुर्थी", "पंचमी", "षष्ठी", "सप्तमी", 
            "अष्टमी", "नवमी", "दशमी", "एकादशी", "द्वादशी", "त्रयोदशी", "चतुर्दशी", "पूर्णिमा/अमावस्या"
        ]
        tithi_day = min(lunar_day if lunar_day <= 15 else lunar_day - 15, 15) - 1
        tithi = f"{paksha} {tithi_names[tithi_day]}"
        
        # Calculate sunrise/sunset (simplified - varies by location)
        sunrise = "06:30"
        sunset = "18:45"
        
        return {
            "date": target_date.isoformat(),
            "tithi": tithi,
            "nakshatra": self.nakshatras[nakshatra_index].value[1],
            "yoga": self.yogas[yoga_index].value[1],
            "karana": self.karanas[karana_index].value[1],
            "sunrise": sunrise,
            "sunset": sunset,
            "moonrise": "23:15",  # Simplified
            "moonset": "11:30",   # Simplified
            "auspicious_time": self._calculate_auspicious_time(target_date),
            "inauspicious_time": self._calculate_inauspicious_time(target_date),
            "special_notes": self._get_special_notes(target_date)
        }
    
    def _calculate_auspicious_time(self, target_date: date) -> str:
        """Calculate auspicious muhurat times"""
        # Simplified calculation - in production, use proper muhurat calculations
        weekday = target_date.weekday()
        
        auspicious_times = {
            0: "07:00-09:00, 14:00-16:00",  # Monday
            1: "08:00-10:00, 15:00-17:00",  # Tuesday
            2: "06:00-08:00, 13:00-15:00",  # Wednesday
            3: "09:00-11:00, 16:00-18:00",  # Thursday
            4: "07:30-09:30, 14:30-16:30",  # Friday
            5: "08:30-10:30, 15:30-17:30",  # Saturday
            6: "06:30-08:30, 13:30-15:30",  # Sunday
        }
        
        return auspicious_times.get(weekday, "07:00-09:00, 14:00-16:00")
    
    def _calculate_inauspicious_time(self, target_date: date) -> str:
        """Calculate inauspicious Rahu Kaal times"""
        # Simplified Rahu Kaal calculation
        weekday = target_date.weekday()
        
        rahu_kaal = {
            0: "07:30-09:00",   # Monday
            1: "15:00-16:30",   # Tuesday
            2: "12:00-13:30",   # Wednesday
            3: "13:30-15:00",   # Thursday
            4: "10:30-12:00",   # Friday
            5: "09:00-10:30",   # Saturday
            6: "16:30-18:00",   # Sunday
        }
        
        return rahu_kaal.get(weekday, "12:00-13:30")
    
    def _get_special_notes(self, target_date: date) -> str:
        """Get special notes for the date"""
        weekday = target_date.weekday()
        
        if weekday == 0:  # Monday
            return "सोमवार - भगवान शिव की पूजा का दिन"
        elif weekday == 1:  # Tuesday
            return "मंगलवार - हनुमान जी की पूजा का दिन"
        elif weekday == 2:  # Wednesday
            return "बुधवार - गणेश जी की पूजा का दिन"
        elif weekday == 3:  # Thursday
            return "गुरुवार - बृहस्पति देव और गुरु की पूजा का दिन"
        elif weekday == 4:  # Friday
            return "शुक्रवार - लक्ष्मी माता की पूजा का दिन"
        elif weekday == 5:  # Saturday
            return "शनिवार - शनि देव की पूजा का दिन"
        else:  # Sunday
            return "रविवार - सूर्य देव की पूजा का दिन"
    
    def get_auspicious_dates_for_content_scheduling(self, start_date: date, end_date: date) -> List[Dict]:
        """Get auspicious dates for scheduling religious content"""
        auspicious_dates = []
        current_date = start_date
        
        while current_date <= end_date:
            panchang = self.generate_daily_panchang(current_date)
            
            # Check if it's an auspicious day based on tithi and nakshatra
            is_auspicious = False
            auspicious_reason = []
            
            # Thursdays are generally auspicious
            if current_date.weekday() == 3:
                is_auspicious = True
                auspicious_reason.append("गुरुवार - विशेष शुभ दिन")
            
            # Check for auspicious nakshatras
            auspicious_nakshatras = ["रोहिणी", "पुष्य", "उत्तरा फाल्गुनी", "हस्त", "श्रवण", "धनिष्ठा", "उत्तराभाद्रपदा"]
            if panchang["nakshatra"] in auspicious_nakshatras:
                is_auspicious = True
                auspicious_reason.append(f"शुभ नक्षत्र: {panchang['nakshatra']}")
            
            # Check for festivals
            festivals = self.get_festivals_for_month(current_date.month, current_date.year)
            for festival in festivals:
                if festival["date"] == current_date.isoformat():
                    is_auspicious = True
                    auspicious_reason.append(f"त्योहार: {festival['hindi_name']}")
            
            if is_auspicious:
                auspicious_dates.append({
                    "date": current_date.isoformat(),
                    "reasons": auspicious_reason,
                    "panchang": panchang,
                    "recommended_content_types": self._get_recommended_content_types(current_date, panchang)
                })
            
            current_date += timedelta(days=1)
        
        return auspicious_dates
    
    def _get_recommended_content_types(self, target_date: date, panchang: Dict) -> List[str]:
        """Get recommended content types for a specific date"""
        recommendations = ["rashifal", "panchang"]  # Always recommend these
        
        weekday = target_date.weekday()
        
        if weekday == 0:  # Monday
            recommendations.extend(["shiva_content", "mantra"])
        elif weekday == 1:  # Tuesday
            recommendations.extend(["hanuman_content", "strength_mantras"])
        elif weekday == 3:  # Thursday
            recommendations.extend(["guru_teachings", "spiritual_wisdom"])
        elif weekday == 4:  # Friday
            recommendations.extend(["lakshmi_content", "prosperity_mantras"])
        
        # Check for Ekadashi (11th day)
        if "एकादशी" in panchang.get("tithi", ""):
            recommendations.extend(["vrat_kathas", "vishnu_content"])
        
        # Check for Purnima (full moon)
        if "पूर्णिमा" in panchang.get("tithi", ""):
            recommendations.extend(["meditation_content", "spiritual_practices"])
        
        return recommendations

# Global service instance
hindu_calendar_service = HinduCalendarService()