args = ""
For I = 0 to Wscript.Arguments.Count - 1
  args = args & """" & WScript.Arguments(i) & """ "
Next

CreateObject("Wscript.Shell").Run args, 0, False