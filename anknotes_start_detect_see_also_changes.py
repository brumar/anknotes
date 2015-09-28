import sys
inAnki='anki' in sys.modules

if not inAnki:
    from anknotes import detect_see_also_changes
    detect_see_also_changes.main()