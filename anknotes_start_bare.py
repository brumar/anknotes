try:
    from aqt.utils import getText
    isAnki = True
except:
    isAnki = False

if not isAnki:
    from anknotes import bare
    bare.main_bare()