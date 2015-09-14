from anknotes.db import *
def upperFirst(name):
    return name[0].upper() + name[1:]

class EvernoteStruct(object):
    success = False
    Name = ""
    Guid = ""
    __sql_columns__ = "name"
    __sql_table__ = TABLES.EVERNOTE.TAGS
    __sql_where__ = "guid"
    def getFromDB(self):
        query = "SELECT %s FROM %s WHERE %s = '%s'" % (', '.join(self.__sql_columns__), self.__sql_table__, self.__sql_where__,
                                                       getattr(self, upperFirst(self.__sql_where__)))
        result = ankDB().first(query)
        if result:
            self.success = True
            i = 0
            for c in self.__sql_columns__:
                setattr(self, upperFirst(c), result[i])
                i += 1
        else:
            self.success = False
        return self.success

    def __init__(self, **kwargs):
        if isinstance(self.__sql_columns__, str): self.__sql_columns__ = [self.__sql_columns__]
        # if isinstance(self.__sql_where__, str): self.__sql_where__ = [self.__sql_where__]
        for v in [].extend(self.__sql_columns__).append(self.__sql_where__):
            if v == "fetch_" + self.__sql_where__:
                setattr(self, upperFirst(self.__sql_where__), kwargs[v])
                self.getFromDB()
            elif v in kwargs: setattr(self, upperFirst(v), kwargs[v])

class EvernoteNotebook(EvernoteStruct):
    Stack = ""
    __sql_columns__ = ["name", "stack"]
    __sql_table__ = TABLES.EVERNOTE.NOTEBOOKS

class EvernoteTag(object):
    ParentGuid = ""
    __sql_columns__ = ["name", "parentGuid"]
    __sql_table__ = TABLES.EVERNOTE.TAGS