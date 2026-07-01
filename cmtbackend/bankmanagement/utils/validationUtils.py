from datetime import datetime


# Check if date is in valid format
def isDateValid(date_string):
    formats = [
        "%Y-%m-%d",  # YYYY-MM-DD
        "%m-%d-%Y",  # MM-DD-YYYY
        "%d-%m-%Y",  # DD-MM-YYYY
        "%Y/%m/%d",  # YYYY/MM/DD
        "%m/%d/%Y",  # MM/DD/YYYY
        "%d/%m/%Y",  # DD/MM/YYYY
        "%Y.%m.%d",  # YYYY.MM.DD
        "%m.%d.%Y",  # MM.DD.YYYY
        "%d.%m.%Y",  # DD.MM.YYYY
    ]

    for fmt in formats:
        try:
            date_str = str(date_string).replace(" 00:00:00", "")
            datetime.strptime(date_str, fmt)
            return True
        # Return True if parsing succeeds
        except ValueError:
            pass
        # Continue to the next format if parsing fails

    return False
