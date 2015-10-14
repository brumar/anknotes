import sys

if not 'anki' in sys.modules:
    from anknotes import detect_see_also_changes
    detect_see_also_changes.main()