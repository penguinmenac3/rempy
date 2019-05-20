class ConsoleState(object):
    def __init__(self):
        self.line = 0
        self.line_version = 0
        self.index = 0


class ConsoleBuffer(object):
    def __init__(self):
        self.__value = ""
        self.__latest_new_line = 0
        self.__current_line = 0
        self.__current_line_iter = 0
        self.__theoretical_length = 0

    def append(self, character: str):
        if character == "\r":
            self.__value = self.__value[:self.__latest_new_line]
            self.__current_line_iter += 1
        elif character == "\n":
            self.__latest_new_line = len(self.__value)
            self.__current_line_iter = 0
            self.__current_line += 1
        self.__value += character
        self.__theoretical_length += 1

    def get_update(self, state: ConsoleState):
        # if we are in the current line but the line version is wrong update from the begining of the line.
        if state.line_version < self.__current_line_iter and state.line == self.__current_line:
            update = self.__value[(self.__latest_new_line):]
        else:
            update = self.__value[state.index:]
        state.index = len(self.__value)
        state.line = self.__current_line
        state.line_version = self.__current_line_iter
        return update
