from enum import Enum


class AutoNumber(Enum):
    def __new__(cls, child=None, offsetLambda=None):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._id_ = value
        obj._parent_ = None
        if hasattr(child, '_parent_'):
            child._parent_ = obj
        obj._child_ = child
        obj._value_ = value
        obj._offset_lambda_ = offsetLambda
        return obj

    # def __value__(self):
    # return self.__child__

    def __getattr__(self, name):
        my_getattr = getattr(self.child(), name, None)
        if my_getattr:
            if callable(my_getattr): return self.child().my_getattr()
            return my_getattr
        return getattr(Enum, name)

    def child(self):
        return self._child_

    def id(self):
        return self._id_

    def myParent(self):
        my_parent_getattr = getattr(self, '__parent__', None)
        if not my_parent_getattr: return None
        if callable(my_parent_getattr):
            return my_parent_getattr()
        else:
            return my_parent_getattr

    def myParentGetAttr(self, attrName):
        my_parent = self.myParent()
        if not my_parent: return None
        my_parent_attr_getattr = getattr(my_parent, attrName, None)
        if not my_parent_attr_getattr: return None
        if callable(my_parent_attr_getattr):
            return my_parent_attr_getattr()
        else:
            return my_parent_attr_getattr

    def fullIndex(self):
        fullIndex = self.value
        my_parent_id = self.myParentGetAttr('id')
        if my_parent_id:
            fullIndex = str(my_parent_id) + '.' + str(fullIndex)
        return fullIndex

    def fullName(self):
        fullName = self.name
        my_parent_name = self.myParentGetAttr('name')
        if my_parent_name:
            fullName = my_parent_name + '.' + fullName
        return fullName

    def fullId(self):
        fullId = self.id()
        my_parent_id = self.myParentGetAttr('id')
        if my_parent_id:
            fullId = str(my_parent_id) + '.' + str(fullId)
        return fullId

    def offset(self, level=None):
        if level and self._offset_lambda_:
            o = self._offset_lambda_(level)
            if isinstance(o, int):
                o = o, o
            return o
        if not hasattr(self, 'offset_start_static'):
            o = self.id()
        else:
            o = self.offset_start_static()
        return o, o

    def offset_as_scalar(self, titlePart=None, count=None):
        o = self.offset(count)
        print " * LEVEL CHECK FOR lvl %s ~ Result %s" % (str(titlePart), str(o))
        if not isinstance(o, int):
            try:
                range_tuple = titlePart.offset(count)
                if range_tuple[0] == range_tuple[1]:
                    o = range_tuple[0]
                else:
                    print "Unexpected range tuple for titlePart offset for offset_as_scalar. Offset: %s " % str(
                        range_tuple)
            except:
                print "Fail - "
        return o

    def offset_start(self, level):
        return self.offset(level)[0]

    def offset_end(self, level):
        return self.offset(level)[1]

        # class Evernote:
        # class Notes:
        # class Note:
        # class Title:


class EvernoteTitleLevels:
    ################## CLASS Sections ################
    class Sections(AutoNumber):
        class Scope(AutoNumber):
            Topic, Part, Chapter = range(1, 4)

            def __parent__(self):
                return Sections.Scope

            def offset_start_static(self):
                return 0 + self.id()

        class Section(AutoNumber):
            Section, Subsection, Heading, Subheading = range(1, 5)

            def __parent__(self):
                return Sections.Section

            def offset_start_static(self):
                return Sections.Scope.Chapter.offset() + self.id()

        class Note(AutoNumber):
            Note, Subnote = range(1, 3)

            def __parent__(self):
                return Sections.Note

            def offset_start_static(self):
                return Sections.Section.Subheading.offset() + self.id()

        class Collection(AutoNumber):
            Paragraphs, Lists = range(1, 3)

            def __parent__(self):
                return Sections.Collection

            def __child__(self):
                return self

            def offset_start_static(self):
                return Sections.Note.Subnote.offset() + self.id()

        class Paragraph(AutoNumber):
            Paragraph, List, Facts = range(1, 4)

            def __parent__(self):
                return Sections.Paragraph

            def offset_start_static(self):
                return Sections.Collection.Lists.offset() + self.id()

        class Item(AutoNumber):
            ListItem, Fact = range(1, 3)

            def __parent__(self):
                return Sections.Item

            def offset_start_static(self):
                return Sections.Paragraph.Facts.offset() + self.id()

                ################## End CLASS Sections ################

    class Parts(AutoNumber):
        Full = (0, lambda l: (1, l))
        Root = (133, lambda l: 1)
        Name = (166, lambda l: l)
        Base = (300, lambda l: (2, l))
        Parent = (433, lambda l: l - 1)
        Child = (466, lambda l: l + 1)

    class Levels(AutoNumber):
        Root, Subject, Topic, Subtopic, Section, Heading, Entry = range(1, 8)
