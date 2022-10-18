#------------------------------------------------------------------------
import os
import N10X
import re

#------------------------------------------------------------------------
# Vim style editing
#
# To enable Vim editing set Vim to true in the 10x settings file
#
#------------------------------------------------------------------------
g_VimEnabled = False

g_CommandMode = "insert"

g_PrevCommand = None
g_PrevInsert = None
g_RepeatCount = None

g_VisualMode = "none"				# "none", "standard", "line"
g_VisualModeStartPos = None

g_HandingKey = False
g_AwaitingNextCharacter = False
g_Timer = 0
g_ExitInsertMode = None

g_YankMode = "selection"			# "selection", "line", "paragraph"

#------------------------------------------------------------------------
# Modes

#------------------------------------------------------------------------
def EnterInsertMode():
	ExitVisualMode()
	global g_CommandMode
	if g_CommandMode != "insert":
		g_CommandMode = "insert"
		N10X.Editor.SetCursorMode("Underscore")
		N10X.Editor.ResetCursorBlink()

#------------------------------------------------------------------------
def EnterCommandMode():
	global g_CommandMode
	if g_CommandMode != "normal":
		g_CommandMode = "normal"
		SetPrevCommand(None)
		N10X.Editor.SetCursorMode("Block")
		N10X.Editor.ResetCursorBlink()

#------------------------------------------------------------------------
def EnterVisualMode(mode):
	global g_VisualMode
	global g_VisualModeStartPos
	if g_VisualMode == "none":
		g_VisualModeStartPos = N10X.Editor.GetCursorPos()
	g_VisualMode = mode
	UpdateVisualModeSelection()

#------------------------------------------------------------------------
def ExitVisualMode():
	global g_VisualMode
	if g_VisualMode != "none":
		g_VisualMode = "none"
		N10X.Editor.RemoveCursor(1)

#------------------------------------------------------------------------
# Misc

#------------------------------------------------------------------------
def IsCommandPrefix(c):
	return \
		c == "c" or \
		c == "d" or \
		c == "g" or \
		c == ">" or \
		c == "<" or \
		c == "y" or \
		c == "r" or \
		c == "ci" or \
		c == "ya" or \
		c == "yi" or \
		c == "va" or \
		c == "vi" or \
		re.search(r"y\d+$", c) != None or \
		re.search(r"d\d+$", c) != None

#------------------------------------------------------------------------
def SetPrevCommand(c):
	global g_PrevCommand
	if g_CommandMode == "normal" and g_PrevCommand != c:
		g_PrevCommand = c
		if c:
			N10X.Editor.SetCursorMode("HalfBlock")
		else:
			N10X.Editor.SetCursorMode("Block")

#------------------------------------------------------------------------
def GetAndClearRepeatCount():
	global g_RepeatCount
	repeat_count = 1
	if g_RepeatCount != None:
		repeat_count = g_RepeatCount
		g_RepeatCount = None
	return repeat_count

#------------------------------------------------------------------------
def RepeatedCommand(command):
	repeat_count = GetAndClearRepeatCount()
	for i in range(repeat_count):
		if callable(command):
			command()
		else:
			N10X.Editor.ExecuteCommand(command)
			
#------------------------------------------------------------------------
def RepeatedEditCommand(command):
	N10X.Editor.PushUndoGroup()
	RepeatedCommand(command)
	N10X.Editor.PopUndoGroup()

#------------------------------------------------------------------------
def GetLengthWithoutNewline(text):
	length = len(text)
	if text.endswith("\r\n"):
		length -= 2
	elif text.endswith("\n"):
		length -= 1
	return length

#------------------------------------------------------------------------
def UpdateVisualModeSelection():
	global g_VisualMode
	global g_VisualModeStartPos
	
	cursor_pos = N10X.Editor.GetCursorPos()

	if g_VisualMode == "standard":
		N10X.Editor.SetSelection(g_VisualModeStartPos, cursor_pos, cursor_index=1)
		
	elif g_VisualMode == "line":
		start_line = min(g_VisualModeStartPos[1], cursor_pos[1])
		end_line = max(g_VisualModeStartPos[1], cursor_pos[1])
		N10X.Editor.SetSelection((0, start_line), (0, end_line + 1), cursor_index=1)

	N10X.Editor.SetCursorVisible(1, False)

#------------------------------------------------------------------------
def SubmitVisualModeSelection():
	global g_VisualMode
	if g_VisualMode != "none":
		start_pos, end_pos = N10X.Editor.GetCursorSelection(cursor_index=1)
		ExitVisualMode()
		N10X.Editor.SetSelection(start_pos, end_pos)
			
#------------------------------------------------------------------------
# Command Functions

#------------------------------------------------------------------------
# NOTE: Vim tries to maintain the x position, but not sure of the exact rules.
# This screws up when the x coordinate does not exist, but is workable.
def MoveToStartOfFile():
	cursor_pos = N10X.Editor.GetCursorPos()
	N10X.Editor.SetCursorPos((cursor_pos[0], 0))

#------------------------------------------------------------------------
def MoveToEndOfFile():
	cursor_pos = N10X.Editor.GetCursorPos()
	line_count = N10X.Editor.GetLineCount()

	N10X.Editor.SetCursorPos((cursor_pos[0], line_count-1))

#------------------------------------------------------------------------
def MoveToStartOfLine():
	cursor_pos = N10X.Editor.GetCursorPos()
	N10X.Editor.SetCursorPos((0, cursor_pos[1]))
	line = N10X.Editor.GetLine(cursor_pos[1])
#------------------------------------------------------------------------
def MoveToEndOfLine():
	cursor_pos = N10X.Editor.GetCursorPos()
	line = N10X.Editor.GetLine(cursor_pos[1])
	N10X.Editor.SetCursorPos((GetLengthWithoutNewline(line), cursor_pos[1]))

#------------------------------------------------------------------------
def IsWordChar(c):
	return \
		(c >= 'a' and c <= 'z') or \
		(c >= 'A' and c <= 'Z') or \
		(c >= '0' and c <= '9') or \
		c == '_'

#------------------------------------------------------------------------
def IsNotWordChar(c):
	return \
		re.search(r"[-!$%^&*()_+|~=`{}\[\]:\";'<>?,.\/]", c) != None

#------------------------------------------------------------------------
def IsInsideWord(cursor_pos):
	line = N10X.Editor.GetLine(cursor_pos[1])
	if cursor_pos[0] > 0 and cursor_pos[0] < len(line):
		if IsWordChar(line[cursor_pos[0] - 1]) and IsWordChar(line[cursor_pos[0] + 1]):
			return True

#------------------------------------------------------------------------
def IsEndOfWord(cursor_pos):
	line = N10X.Editor.GetLine(cursor_pos[1])
	if cursor_pos[0] < len(line):
		if IsWordChar(line[cursor_pos[0] + 1]) == False:
			return True

#------------------------------------------------------------------------
def GetWordEnd():
	cursor_pos = N10X.Editor.GetCursorPos()
	line = N10X.Editor.GetLine(cursor_pos[1])
	i = cursor_pos[0]
	if i < len(line):
		is_word_char = IsWordChar(line[i])
		while i < len(line):
			if IsWordChar(line[i]) != is_word_char:
				break
			i += 1
	return i

#------------------------------------------------------------------------
def CutToEndOfWordAndInsert():
	repeat_count = GetAndClearRepeatCount()
	cursor_pos = N10X.Editor.GetCursorPos()

	for i in range(repeat_count - 1):
		N10X.Editor.ExecuteCommand("MoveCursorNextWord")
	word_end_pos = GetWordEnd()
	N10X.Editor.SetSelection(cursor_pos, (word_end_pos, cursor_pos[1]))
	N10X.Editor.ExecuteCommand("Cut")

	EnterInsertMode()

#------------------------------------------------------------------------
def CutWordAndInsert():
	repeat_count = GetAndClearRepeatCount()
	cursor_pos = N10X.Editor.GetCursorPos()
	line = N10X.Editor.GetLine(cursor_pos[1])

	if IsNotWordChar(line[cursor_pos[0]]):
		EnterInsertMode()
		return

	if line.isspace():
		EnterInsertMode()
		return

	N10X.Editor.PushUndoGroup()
	if IsInsideWord(cursor_pos) or IsEndOfWord(cursor_pos):
		N10X.Editor.ExecuteCommand("MoveCursorPrevWord")
		
	cursor_pos = N10X.Editor.GetCursorPos()
	word_end_pos = GetWordEnd()
	N10X.Editor.SetSelection(cursor_pos, (word_end_pos, cursor_pos[1]))
	N10X.Editor.ExecuteCommand("Cut")
	N10X.Editor.PopUndoGroup()

	EnterInsertMode()

#------------------------------------------------------------------------
def CutToEndOfLine():
	cursor_pos = N10X.Editor.GetCursorPos()

	line = N10X.Editor.GetLine(cursor_pos[1])
	line_end_pos = len(line)
	N10X.Editor.SetSelection(cursor_pos, (line_end_pos, cursor_pos[1]))
	N10X.Editor.ExecuteCommand("Cut")

#------------------------------------------------------------------------
def CutToEndOfLineAndInsert():
	CutToEndOfLine()
	EnterInsertMode()

#------------------------------------------------------------------------
def CutToEndOfWord():
	repeat_count = GetAndClearRepeatCount()
	cursor_pos = N10X.Editor.GetCursorPos()

	for i in range(repeat_count - 1):
		N10X.Editor.ExecuteCommand("MoveCursorNextWord")
	word_end_pos = GetWordEnd()
	N10X.Editor.SetSelection(cursor_pos, (word_end_pos, cursor_pos[1]))
	N10X.Editor.ExecuteCommand("Cut")

#------------------------------------------------------------------------
def DeleteLine():
	global g_VisualMode
	SubmitVisualModeSelection()
	cursor_pos = N10X.Editor.GetCursorPos()
	repeat_count = GetAndClearRepeatCount()

	if g_VisualMode != "none":
		SubmitVisualModeSelection()
	else:
		cursor_pos = N10X.Editor.GetCursorPos()
		N10X.Editor.SetSelection((0, cursor_pos[1]), (0, cursor_pos[1] + repeat_count))
		
	N10X.Editor.ExecuteCommand("Cut")
	N10X.Editor.SetCursorPos(cursor_pos)

#------------------------------------------------------------------------
def JoinLine():
	N10X.Editor.SendKey("Down")
	DeleteLine()
	N10X.Editor.SendKey("Up")
	MoveToEndOfLine()
	cursor_pos = N10X.Editor.GetCursorPos()
	N10X.Editor.InsertText(" ")
	N10X.Editor.ExecuteCommand("Paste")
	N10X.Editor.SetCursorPos(cursor_pos) # Need to set the cursor pos to right before join

#------------------------------------------------------------------------
def SelectParagraph(cursor_pos, all):
	cursor_rev_pos = cursor_pos[1]
	cursor_fwd_pos = cursor_pos[1]
	while cursor_rev_pos > 0 and N10X.Editor.GetLine(cursor_rev_pos).isspace() != True:
		cursor_rev_pos -= 1
	while cursor_fwd_pos <= N10X.Editor.GetLineCount() and N10X.Editor.GetLine(cursor_fwd_pos).isspace() != True:
		cursor_fwd_pos += 1
	if N10X.Editor.GetLine(cursor_rev_pos).isspace() == True:
		cursor_rev_pos += 1;
	if all == False and N10X.Editor.GetLine(cursor_fwd_pos).isspace() == True:
		cursor_fwd_pos -= 1;
	last_line = N10X.Editor.GetLine(cursor_fwd_pos)
	N10X.Editor.SetSelection((0, cursor_rev_pos), (len(last_line), cursor_fwd_pos))

#------------------------------------------------------------------------
def SelectParagraphVisual(cursor_pos, all):
	global g_VisualMode
	global g_VisualModeStartPos

	cursor_rev_pos = cursor_pos[1]
	cursor_fwd_pos = cursor_pos[1]
	while cursor_rev_pos > 0 and N10X.Editor.GetLine(cursor_rev_pos).isspace() != True:
		cursor_rev_pos -= 1
	while cursor_fwd_pos <= N10X.Editor.GetLineCount() and N10X.Editor.GetLine(cursor_fwd_pos).isspace() != True:
		cursor_fwd_pos += 1
	if N10X.Editor.GetLine(cursor_rev_pos).isspace() == True:
		cursor_rev_pos += 1;
	if all == False and N10X.Editor.GetLine(cursor_fwd_pos).isspace() == True:
		cursor_fwd_pos -= 1;
	last_line = N10X.Editor.GetLine(cursor_fwd_pos)
	g_VisualModeStartPos = (0, cursor_rev_pos)
	N10X.Editor.SetSelection((0, cursor_rev_pos), (len(last_line), cursor_fwd_pos), cursor_index=1)
	g_VisualMode = "line"
		
#------------------------------------------------------------------------
def Yank(lines = 0, direction = 0):
	global g_VisualMode
	global g_YankMode

	repeat_count = GetAndClearRepeatCount()
	cursor_pos = N10X.Editor.GetCursorPos()
	if direction == -1 and cursor_pos[1] - lines < 0:
		lines = cursor_pos[1]
	line = N10X.Editor.GetLine(cursor_pos[1] + lines * direction)
	if direction == -1:
		N10X.Editor.SetSelection((0, cursor_pos[1] + lines * direction), (len(line), cursor_pos[1]))
	else:
		N10X.Editor.SetSelection((0, cursor_pos[1]), (len(line), cursor_pos[1] + lines * direction))
	g_YankMode = "line"
		
	N10X.Editor.ExecuteCommand("Copy")
	N10X.Editor.SetCursorPos(cursor_pos)

#------------------------------------------------------------------------
def YankParagraph(all):
	global g_YankMode
	cursor_pos = N10X.Editor.GetCursorPos()
	SelectParagraph(cursor_pos, all)
	N10X.Editor.ExecuteCommand("Copy")
	N10X.Editor.SetCursorPos(cursor_pos)
	if all == True:
		g_YankMode = "paragraph"
	else:
		g_YankMode = "line"

#------------------------------------------------------------------------
def CutLines(lines = 0, direction = 0):
	global g_VisualMode
	global g_YankMode

	repeat_count = GetAndClearRepeatCount()
	cursor_pos = N10X.Editor.GetCursorPos()
	if direction == -1 and cursor_pos[1] - lines < 0:
		lines = cursor_pos[1]

	if direction == -1:
		line = N10X.Editor.GetLine(cursor_pos[1])
		N10X.Editor.SetSelection((0, cursor_pos[1] + lines * direction), (len(line), cursor_pos[1]))
	else:
		line = N10X.Editor.GetLine(cursor_pos[1] + lines * direction)
		N10X.Editor.SetSelection((0, cursor_pos[1]), (len(line), cursor_pos[1] + lines * direction))
	g_YankMode = "line"
		
	N10X.Editor.PushUndoGroup()
	N10X.Editor.ExecuteCommand("Cut")
	N10X.Editor.ExecuteCommand("DeleteLine")
	MoveToStartOfLine();
	line = N10X.Editor.GetLine(N10X.Editor.GetCursorPos()[1])
	if line.isspace() == False and line[0].isspace():
		N10X.Editor.ExecuteCommand("MoveCursorNextWord")
	N10X.Editor.PopUndoGroup()

#------------------------------------------------------------------------
def YankSelection():
	global g_VisualMode
	global g_YankMode

	SubmitVisualModeSelection()
	cursor_pos = N10X.Editor.GetCursorPos()
	if g_VisualMode == "standard":
		g_YankMode = "selection"
	else:
		g_YankMode = "line"
		
	N10X.Editor.ExecuteCommand("Copy")
	N10X.Editor.SetCursorPos(cursor_pos)

#------------------------------------------------------------------------
def ReplaceLine():
	N10X.Editor.PushUndoGroup()
	DeleteLine()
	N10X.Editor.ExecuteCommand("InsertLine")
	EnterInsertMode()
	N10X.Editor.PopUndoGroup()

#------------------------------------------------------------------------
def DeleteCharacters():
	global g_VisualMode
	if g_VisualMode != "none":
		SubmitVisualModeSelection()
	else:
		repeat_count = GetAndClearRepeatCount()
		cursor_pos = N10X.Editor.GetCursorPos()
		N10X.Editor.SetSelection(cursor_pos, (cursor_pos[0] + repeat_count, cursor_pos[1]))
	N10X.Editor.ExecuteCommand("Cut")

#------------------------------------------------------------------------
def AppendNewLineBelow():
	ExitVisualMode()
	EnterInsertMode()
	N10X.Editor.PushUndoGroup()
	MoveToEndOfLine()
	N10X.Editor.SendKey("Enter")
	N10X.Editor.PopUndoGroup()

#------------------------------------------------------------------------
def CapitaliseSelection():
	global g_VisualMode
	if g_VisualMode != "none":
		SubmitVisualModeSelection()
	else:
		repeat_count = GetAndClearRepeatCount()
		cursor_pos = N10X.Editor.GetCursorPos()
		N10X.Editor.SetSelection(cursor_pos, (cursor_pos[0] + repeat_count, cursor_pos[1]))
	N10X.Editor.ExecuteCommand("MakeSelectionUppercase")

#------------------------------------------------------------------------
def PasteAfter():
	global g_VisualMode
	global g_YankMode
	if g_VisualMode != "none":
		SubmitVisualModeSelection()

	if g_YankMode == "line":
		N10X.Editor.PushUndoGroup()
		MoveToEndOfLine()
		EnterInsertMode()
		N10X.Editor.SendKey("Enter")
		EnterCommandMode()
		MoveToStartOfLine()
		N10X.Editor.ExecuteCommand("Paste")
		MoveToStartOfLine()
		N10X.Editor.ExecuteCommand("MoveCursorNextWord")
		N10X.Editor.PopUndoGroup()

	elif g_YankMode == "selection":
		N10X.Editor.PushUndoGroup()
		N10X.Editor.SendKey("Right")
		N10X.Editor.ExecuteCommand("Paste")
		N10X.Editor.PopUndoGroup()

	elif g_YankMode == "paragraph":
		N10X.Editor.PushUndoGroup()
		MoveToEndOfLine()
		EnterInsertMode()
		N10X.Editor.SendKey("Enter")
		cursor_pos = N10X.Editor.GetCursorPos()
		MoveToStartOfLine()
		N10X.Editor.ExecuteCommand("Paste")
		EnterCommandMode()
		N10X.Editor.SetCursorPos(cursor_pos)
		N10X.Editor.PopUndoGroup()

#------------------------------------------------------------------------
def PasteBefore():
	global g_VisualMode
	global g_YankMode

	if g_VisualMode != "none":
		SubmitVisualModeSelection()

	if g_YankMode == "line":
		N10X.Editor.PushUndoGroup()
		N10X.Editor.ExecuteCommand("InsertLine");
		MoveToStartOfLine()
		N10X.Editor.ExecuteCommand("Paste")
		MoveToStartOfLine()
		N10X.Editor.ExecuteCommand("MoveCursorNextWord")
		N10X.Editor.PopUndoGroup()

	elif g_YankMode == "selection":
		N10X.Editor.ExecuteCommand("Paste")

	elif g_YankMode == "paragraph":
		N10X.Editor.PushUndoGroup()
		N10X.Editor.ExecuteCommand("InsertLine");
		cursor_pos = N10X.Editor.GetCursorPos()
		MoveToStartOfLine()
		N10X.Editor.ExecuteCommand("Paste")
		N10X.Editor.SetCursorPos(cursor_pos)
		N10X.Editor.PopUndoGroup()

#------------------------------------------------------------------------
def ReplaceCursor(c):
	cursor_pos = N10X.Editor.GetCursorPos()
	N10X.Editor.PushUndoGroup()
	N10X.Editor.SetSelection(cursor_pos, (cursor_pos[0] + 1, cursor_pos[1]))
	N10X.Editor.ExecuteCommand("Cut")
	N10X.Editor.InsertText(c)
	N10X.Editor.SetCursorPos(cursor_pos)
	N10X.Editor.PopUndoGroup()

#------------------------------------------------------------------------
def SubstituteCursor():
	cursor_pos = N10X.Editor.GetCursorPos()
	N10X.Editor.SetSelection(cursor_pos, (cursor_pos[0] + 1, cursor_pos[1]))
	N10X.Editor.ExecuteCommand("Cut")
	EnterInsertMode()

#------------------------------------------------------------------------

# Key Intercepting

#------------------------------------------------------------------------
def HandleCommandModeChar(c):

	global g_PrevCommand
	global g_AwaitingNextCharacter

	if g_AwaitingNextCharacter:
		if g_PrevCommand == "r":
			ReplaceCursor(c)
		g_AwaitingNextCharacter = False
		SetPrevCommand(None)
		return

	command = c
	if g_PrevCommand:
		command = g_PrevCommand + c
	global g_RepeatCount
	is_repeat_key = False

	global g_VisualMode
	global g_YankMode

	if c >= '1' and c <= '9' or (c == '0' and g_RepeatCount != None):
		if g_RepeatCount == None:
			g_RepeatCount = int(c)
		else:
			g_RepeatCount = 10 * g_RepeatCount + int(c)
		is_repeat_key = True

	if g_VisualMode == "none" and command == "i":
		EnterInsertMode()

	elif g_VisualMode != "none" and command == "d":
		DeleteLine()

	elif g_VisualMode != "none" and command == "y":
		YankSelection()

	elif g_VisualMode != "none" and command == "c":
		ReplaceLine()

	elif g_VisualMode != "none" and command == "i":
		g_PrevCommand = "vi"
		command = "vi"

	elif g_VisualMode != "none" and command == "a":
		g_PrevCommand = "va"
		command = "va"

	elif IsCommandPrefix(command):
		SetPrevCommand(command)

	elif command == ":":
		N10X.Editor.ExecuteCommand("ShowCommandPanel")
		N10X.Editor.SetCommandPanelText(":")

	elif command == "v":
		if g_VisualMode == "standard":
			ExitVisualMode()
		else:
			EnterVisualMode("standard")

	elif command == "V":
		if g_VisualMode == "line":
			ExitVisualMode()
		else:
			EnterVisualMode("line")

	elif command == "dd":
		CutLines()

	elif command == "dj":
		CutLines(1, 1)
		
	elif command == "dk":
		CutLines(1, -1)

	elif re.search(r"d\d+j", command) != None:
		CutLines(g_RepeatCount, 1)

	elif re.search(r"d\d+k", command) != None:
		CutLines(g_RepeatCount, -1)

	elif command == "yy":
		Yank()
		
	elif re.search(r"y\d+j", command) != None:
		Yank(g_RepeatCount, 1)

	elif re.search(r"y\d+k", command) != None:
		Yank(g_RepeatCount, -1)

	elif command == "yj":
		Yank(1, 1)

	elif command == "yk":
		Yank(1, -1)

	elif command == "yap":
		YankParagraph(True)

	elif command == "yip":
		YankParagraph(False)

	elif command == "vap":
		cursor_pos = N10X.Editor.GetCursorPos()
		SelectParagraphVisual(cursor_pos, True)

	elif command == "vip":
		cursor_pos = N10X.Editor.GetCursorPos()
		SelectParagraphVisual(cursor_pos, False)

	elif command == "cc":
		ReplaceLine()

	elif command == "P":
		SubmitVisualModeSelection()
		PasteBefore()

	elif command == "h":
		RepeatedCommand(lambda:N10X.Editor.SendKey("Left"));
		UpdateVisualModeSelection()

	elif command == "l":
		RepeatedCommand(lambda:N10X.Editor.SendKey("Right"));
		UpdateVisualModeSelection()

	elif command == "k":
		RepeatedCommand(lambda:N10X.Editor.SendKey("Up"));
		UpdateVisualModeSelection()

	elif command == "j":
		RepeatedCommand(lambda:N10X.Editor.SendKey("Down"));
		UpdateVisualModeSelection()

	if command == "0":
		MoveToStartOfLine()

	elif command == "$":
		MoveToEndOfLine()

	elif command == "b":
		RepeatedCommand("MoveCursorPrevWord")

	elif command == "w":
		RepeatedCommand("MoveCursorNextWord")
		
	elif command == "r":
		g_AwaitingNextCharacter = True

	elif command == "s":
		SubstituteCursor()

	elif command == "dw":
		CutToEndOfWord()

	elif command == "cw":
		CutToEndOfWordAndInsert()
		
	elif command == "ciw":
		CutWordAndInsert()

	elif command == "dW" or command == "D":
		CutToEndOfLine()
		
	elif command == "cW" or command == "C":
		CutToEndOfLineAndInsert()
		
	elif command == "J":
		JoinLine()

	elif command == "I":
		MoveToStartOfLine();
		N10X.Editor.ExecuteCommand("MoveCursorNextWord")
		EnterInsertMode();

	elif command == "a":
		# NOTE: this bugs when trying pressing it at the end of a line.
		# It shouldn't go to the next line, it should just go to the last possible position.
		# This might be a byproduct of not using a block cursor in insertmode, where you
		# actually can't go to the position after the last char.
		N10X.Editor.ExecuteCommand("MoveCursorRight");
		EnterInsertMode();

	elif command == "A":
		MoveToEndOfLine();
		EnterInsertMode();

	elif command == "~":
		CapitaliseSelection()

	elif command == "e":
		cursor_pos = N10X.Editor.GetCursorPos()
		N10X.Editor.SetCursorPos((GetWordEnd(), cursor_pos[1]))

	elif command == "p":
		# In vim, the cursor should "stay with the line."
		# Doing this for P seems to do some weird selection thing.
		SubmitVisualModeSelection()
		PasteAfter()

	elif command == "*":
		RepeatedCommand("FindInFileNextCurrentWord")
		
	elif command == "n":
		RepeatedCommand("FindInFileNext")

	elif command == "N":
		RepeatedCommand("FindInFilePrev")

	elif command == "#":
		RepeatedCommand("FindInFilePrevCurrentWord")

	elif command == "O":
		ExitVisualMode()
		N10X.Editor.ExecuteCommand("InsertLine");
		EnterInsertMode();

	elif command == "o":
		AppendNewLineBelow()

	elif command == "gd":
		ExitVisualMode()
		N10X.Editor.ExecuteCommand("GotoSymbolDefinition");

	# NOTE: in vim, this loops.
	elif command == "gt":
		ExitVisualMode()
		N10X.Editor.ExecuteCommand("NextPanelTab");

	elif command == "gT":
		ExitVisualMode()
		N10X.Editor.ExecuteCommand("PrevPanelTab");

	elif command == "gg":
		MoveToStartOfFile();

	elif command == "G":
		MoveToEndOfFile();

	# NOTE: undo is pretty buggy with P/p stuff -- cursor position gets messed up.
	elif command == "u":
		ExitVisualMode()
		RepeatedCommand("Undo")

	elif command == ">>":
		SubmitVisualModeSelection()
		RepeatedCommand("IndentLine")

	elif command == "<<":
		SubmitVisualModeSelection()
		RepeatedCommand("UnindentLine")

	elif command == "x":
		DeleteCharacters()

	if not IsCommandPrefix(command):
		SetPrevCommand(None)

	# reset repeat count
	if (not is_repeat_key) and (not IsCommandPrefix(command)):
		g_RepeatCount = None

#------------------------------------------------------------------------
def HandleCommandModeKey(key, shift, control, alt):

	global g_HandingKey
	if g_HandingKey:
		return
	g_HandingKey = True

	handled = True

	global g_VisualMode

	pass_through = False

	if key == "Escape":
		ExitVisualMode()
		
	elif key == "H" and alt:
		N10X.Editor.ExecuteCommand("MovePanelFocusLeft")

	elif key == "L" and alt:
		N10X.Editor.ExecuteCommand("MovePanelFocusRight")

	elif key == "J" and alt:
		N10X.Editor.ExecuteCommand("MovePanelFocusDown")

	elif key == "K" and alt:
		N10X.Editor.ExecuteCommand("MovePanelFocusUp")

	elif key == "Up" and g_VisualMode != "none":
		N10X.Editor.SendKey("Up")
		UpdateVisualModeSelection()

	elif key == "Down" and g_VisualMode != "none":
		N10X.Editor.SendKey("Down")
		UpdateVisualModeSelection()

	elif key == "Left" and g_VisualMode != "none":
		N10X.Editor.SendKey("Left")
		UpdateVisualModeSelection()

	elif key == "Right" and g_VisualMode != "none":
		N10X.Editor.SendKey("Right")
		UpdateVisualModeSelection()
	elif key == "PageUp":
		N10X.Editor.SendKey("PageUp")
	elif key == "PageDown":
		N10X.Editor.SendKey("PageDown")
	else:
		handled = False

		pass_through = \
			control or \
			alt or \
			key == "Escape" or \
			key == "Delete" or \
			key == "Backspace" or \
			key == "Up" or \
			key == "Down" or \
			key == "Left" or \
			key == "Right"

	if handled or pass_through:
		global g_RepeatCount
		g_RepeatCount = None
		SetPrevCommand(None)

	g_HandingKey = False
	
	return not pass_through

#------------------------------------------------------------------------
def HandleInsertModeKey(key, shift, control, alt):

	if key == "Escape":
		EnterCommandMode()
		return True

	if key == "C" and control:
		EnterCommandMode()
		return True

#------------------------------------------------------------------------
# 10X Callbacks

#------------------------------------------------------------------------
# Called when a key is pressed.
# Return true to surpress the key
def OnInterceptKey(key, shift, control, alt):
	if N10X.Editor.TextEditorHasFocus():
		global g_CommandMode
		if g_CommandMode == "normal":
			return HandleCommandModeKey(key, shift, control, alt)
		else:
			HandleInsertModeKey(key, shift, control, alt)

#------------------------------------------------------------------------
# Called when a char is to be inserted into the text editor.
# Return true to surpress the char key.
# If we are in command mode surpress all char keys
def OnInterceptCharKey(c):
	if N10X.Editor.TextEditorHasFocus():
		global g_CommandMode
		global g_PrevInsert
		global g_Timer
		global g_ExitInsertMode
		if g_CommandMode == "normal":
			HandleCommandModeChar(c)
			return True
		elif g_ExitInsertMode != None and g_CommandMode == "insert":
			if c == g_ExitInsertMode and g_PrevInsert == None and g_Timer == 0:
				g_Timer = time.time()
				g_PrevInsert = g_ExitInsertMode
				return True
			elif c == g_ExitInsertMode and g_PrevInsert == g_ExitInsertMode and time.time() - g_Timer <= 1:
				g_Timer = 0
				g_PrevInsert = None
				EnterCommandMode()
				return True
			elif c == g_ExitInsertMode and g_PrevInsert == g_ExitInsertMode:
				g_Timer = 0
				g_PrevInsert = None
				N10X.Editor.InsertText(g_ExitInsertMode)
			elif c != g_ExitInsertMode and g_PrevInsert == g_ExitInsertMode:
				g_Timer = 0
				g_PrevInsert = None
				N10X.Editor.InsertText(g_ExitInsertMode)
			
#------------------------------------------------------------------------
def HandleCommandPanelCommand(command):

	if command == ":w":
		N10X.Editor.ExecuteCommand("SaveFile")
		return True

	if command == ":wq":
		N10X.Editor.ExecuteCommand("SaveFile")
		N10X.Editor.ExecuteCommand("CloseFile")
		return True

	if command == ":q":
		N10X.Editor.ExecuteCommand("CloseFile")
		return True

	if command == ":q!":
		N10X.Editor.DiscardUnsavedChanges()
		N10X.Editor.ExecuteCommand("CloseFile")
		return True

#------------------------------------------------------------------------
def EnableVim():
	global g_VimEnabled
	global g_ExitInsertMode
	enable_vim = N10X.Editor.GetSetting("Vim") == "true"
	g_ExitInsertMode = None
	if N10X.Editor.GetSetting("ExitInsertMode"):
		g_ExitInsertMode = N10X.Editor.GetSetting("ExitInsertMode")
		if len(g_ExitInsertMode) > 1:
			g_ExitInsertMode = g_ExitInsertMode[0]

	if g_VimEnabled != enable_vim:
		g_VimEnabled = enable_vim

		if enable_vim:
			print("[vim] Enabling Vim")
			N10X.Editor.AddOnInterceptCharKeyFunction(OnInterceptCharKey)
			N10X.Editor.AddOnInterceptKeyFunction(OnInterceptKey)
			EnterCommandMode()

		else:
			print("[vim] Disabling Vim")
			EnterInsertMode()
			N10X.Editor.ResetCursorMode()
			N10X.Editor.RemoveOnInterceptCharKeyFunction(OnInterceptCharKey)
			N10X.Editor.RemoveOnInterceptKeyFunction(OnInterceptKey)

#------------------------------------------------------------------------
# enable/disable Vim when it's changed in the settings file
def OnSettingsChanged():
	EnableVim()

#------------------------------------------------------------------------
def InitialiseVim():
	EnableVim()

#------------------------------------------------------------------------
N10X.Editor.AddOnSettingsChangedFunction(OnSettingsChanged)
N10X.Editor.AddCommandPanelHandlerFunction(HandleCommandPanelCommand)

N10X.Editor.CallOnMainThread(InitialiseVim)
