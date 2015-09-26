try:
    from aqt.utils import getText
    isAnki = True
except:
    isAnki = False

if not isAnki:
    from anknotes import detect_see_also_changes
    detect_see_also_changes.main()