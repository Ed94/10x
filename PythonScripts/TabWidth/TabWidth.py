import N10X

def TabWidthIncrease():
    curr_width = int(N10X.Editor.GetSetting("TabWidth"))
    N10X.Editor.SetSetting("TabWidth", str(curr_width + 1))

def TabWidthDecrease():
    curr_width = int(N10X.Editor.GetSetting("TabWidth"))
    N10X.Editor.SetSetting("TabWidth", str(curr_width - 1))
