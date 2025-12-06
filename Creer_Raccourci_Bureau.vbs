' Script pour créer un raccourci sur le bureau
' Double-cliquez sur ce fichier pour créer le raccourci

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Obtenir le chemin du bureau
desktopPath = WshShell.SpecialFolders("Desktop")

' Obtenir le chemin du dossier actuel (où se trouve ce script)
scriptPath = fso.GetParentFolderName(WScript.ScriptFullName)

' Chemin vers le fichier bat
batPath = scriptPath & "\Lancer.bat"

' Créer le raccourci
Set shortcut = WshShell.CreateShortcut(desktopPath & "\SEO Juice Analyzer.lnk")
shortcut.TargetPath = batPath
shortcut.WorkingDirectory = scriptPath
shortcut.Description = "Lancer l'outil d'analyse de maillage interne SEO"
shortcut.IconLocation = scriptPath & "\link.ico"
shortcut.Save

MsgBox "Raccourci créé sur le bureau !" & vbCrLf & vbCrLf & "Vous pouvez maintenant lancer l'application en double-cliquant sur 'SEO Juice Analyzer' sur votre bureau.", vbInformation, "Succès"
