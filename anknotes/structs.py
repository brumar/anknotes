from anknotes.db import *
from enum import Enum

# from evernote.edam.notestore.ttypes import NoteMetadata, NotesMetadataList

def upperFirst(name):
    return name[0].upper() + name[1:]

class EvernoteStruct(object):
    success = False
    Name = ""
    Guid = ""
    __sql_columns__ = "name"
    __sql_table__ = TABLES.EVERNOTE.TAGS
    __sql_where__ = "guid"
    __attr_order__ = []

    def keys(self):
        if len(self.__attr_order__) == 0:
            self.__attr_order__ = [].extend(self.__sql_columns__).append(self.__sql_where__)
        return self.__attr_order__

    def items(self):
        lst = []
        for key in self.__attr_order__:
            lst.append(getattr(self, key))
        return lst

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

    def __init__(self, *args, **kwargs):
        if isinstance(self.__sql_columns__, str): self.__sql_columns__ = [self.__sql_columns__]
        i = 0
        for v in args:
            k = self.__attr_order__[i]
            setattr(self, upperFirst(k), v)
            i += 1
        for v in [].extend(self.__sql_columns__).append(self.__sql_where__):
            if v == "fetch_" + self.__sql_where__:
                setattr(self, upperFirst(self.__sql_where__), kwargs[v])
                self.getFromDB()
            elif v in kwargs: setattr(self, upperFirst(v), kwargs[v])

class EvernoteNotebook(EvernoteStruct):
    Stack = ""
    __sql_columns__ = ["name", "stack"]
    __sql_table__ = TABLES.EVERNOTE.NOTEBOOKS

class EvernoteTag(EvernoteStruct):
    ParentGuid = ""
    __sql_columns__ = ["name", "parentGuid"]
    __sql_table__ = TABLES.EVERNOTE.TAGS

class EvernoteTOCEntry(EvernoteStruct):
    RealTitle = ""
    """:type : str"""
    OrderedList = ""
    """
    HTML output of Root Title's Ordererd List
    :type : str
    """
    TagNames = ""
    """:type : str"""
    NotebookGuid = ""
    __attr_order__ = ['realTitle' 'orderedList', 'tagNames', 'notebookGuid']

class EvernoteAPIStatus(Enum):
    Uninitialized, EmptyRequest, Success, RateLimitError, SocketError, UserError, NotFoundError, UnhandledError, Unknown = range(-2, 7)
    # Uninitialized = -100
    # NoParameters = -1
    # Success = 0
    # RateLimitError = 1
    # SocketError = 2
    # UserError = 3
    # NotFoundError = 4
    # UnhandledError = 5
    # Unknown = 100
    
    @property 
    def IsError(self):
        return (self != EvernoteAPIStatus.Unknown and self.value > EvernoteAPIStatus.Success.value)
    
    @property
    def IsSuccessful(self):
        return (self == EvernoteAPIStatus.Success or self == EvernoteAPIStatus.EmptyRequest)
    
    @property
    def IsSuccess(self):
        return (self == EvernoteAPIStatus.Success)

class EvernoteImportType:
    Add, UpdateInPlace, DeleteAndUpdate = range(3)

class EvernoteNoteFetcherResult(object):
    def __init__(self, note=None, status=None, source=-1):
        """

        :type note: EvernoteNotePrototype
        :type status: EvernoteAPIStatus
        """
        if not status: status = EvernoteAPIStatus.Uninitialized
        self.Note = note
        self.Status = status
        self.Source = source

class EvernoteNoteFetcherResults(object):
        Status = EvernoteAPIStatus.Uninitialized
        ImportType = EvernoteImportType.Add
        Local = 0
        Notes = []
        Imported = 0
        Max = 0
        AlreadyUpToDate = 0
        
        @property 
        def DownloadSuccess(self):
            return self.Count == self.Max
            
        @property 
        def AnkiSuccess(self):
            return self.Imported == self.Count 

        @property 
        def TotalSuccess(self):
            return self.DownloadSuccess and self.AnkiSuccess      
        
        @property
        def LocalDownloadsOccurred(self):
            return self.Local > 0
        
        @property 
        def Remote(self):
            return self.Count - self.Local
        
        @property
        def SummaryShort(self):
            add_update_strs = ['New', "Added"] if self.ImportType == EvernoteImportType.Add else  ['Existing', 'Updated In-Place' if  self.ImportType == EvernoteImportType.UpdateInPlace else 'Deleted and Updated']  
            return "%d %s Notes Have Been %s" % (self.Imported, add_update_strs[0], add_update_strs[1])
        
        @property
        def SummaryLines(self):
            add_update_strs = ['New', "Added to"] if self.ImportType == EvernoteImportType.Add else  ['Existing', "%s in" % ('Updated In-Place' if  self.ImportType == EvernoteImportType.UpdateInPlace else 'Deleted and Updated')]  
            add_update_strs[1] += " Anki"
            if self.Max is 0: return []
            ## Evernote Status 
            if self.DownloadSuccess:
                line = "All %d" % self.Max
            else:
                line = "%d of %d" % (self.Count, self.Max)            
            lines=[line + " %s Evernote Metadata Results Were Successfully Downloaded%s." % (add_update_strs[0], (' And %s' % add_update_strs[1]) if self.AnkiSuccess else '')]
            if self.Status.IsError:
                lines.append("An error occurred during download (%s)." % str(self.Status))                
            if self.DownloadSuccess:
                return lines
            if self.AnkiSuccess:
                line = "All %d" % self.Imported
            else:
                line = "%d of %d" % (self.Imported, self.Count)
            lines.append(line + " %s Downloaded Evernote Notes Have Been Successfully %s." % (add_update_strs[0], add_update_strs[1]))
            
            
            if self.LocalDownloadsOccurred:
                tooltip += "<BR> --- %d %s note(s) were unexpectedly found in the local db and did not require an API call." % (self.Local, add_update_strs[0])
                tooltip += "<BR> --- %d %s note(s) required an API call" % (self.Remote, add_update_strs[0])    
            
            if not self.ImportType == EvernoteImportType.Add:
                tooltip += "<BR>%d existing note(s) are already up-to-date with Evernote's servers, so they were not retrieved." % n3
            
            return lines
            
        @property
        def Summary(self):
            lines = self.SummaryLines
            if len(lines) is 0:
                return ''
            return '<BR>   - '.join(lines)
        
        @property 
        def Count(self):
            return len(self.Notes)
            
        @property 
        def EvernoteFails(self):
            return self.Max - self.Count 
            
        @property
        def AnkiFails(self):
            return self.Count - self.Imported
            
        def __init__(self, status=None, local=None):
            """
            :param status:
            :type status : EvernoteAPIStatus
            :param local:
            :return:
            """
            if not status: status = EvernoteAPIStatus.Uninitialized
            if not local: local = 0
            self.Status = status
            self.Local = local
            self.Imported = 0
            self.Notes = []

        def reportResult(self, result):
            """
            :type result : EvernoteNoteFetcherResult
            """
            self.Status = result.Status 
            if self.Status == EvernoteAPIStatus.Success:
                self.Notes.append(result.Note)
                if self.Source == 1:
                    self.Local += 1


class EvernoteImportProgress:
    Anki = None
    """:type : anknotes.Anki.Anki"""
    class _GUIDs:
        Local = None
        class Server: 
            All = None        
            New = None
            class Existing:
                All = None                
                UpToDate = None
                OutOfDate = None 

        def loadNew(self, server_evernote_guids=None):
            if server_evernote_guids:
                self.Server.All = server_evernote_guids
            if not self.Server.All:
                return
            setServer = set(self.Server.All)
            self.Server.New = setServer - set(self.Local)
            self.Server.Existing.All = setServer - set(self.Server.New)

    class Results:
        Adding = None
        """:type : EvernoteNoteFetcherResults"""
        Updating = None 
        """:type : EvernoteNoteFetcherResults"""        
            
    GUIDs = _GUIDs()
    
    @property
    def Adding(self):
        return len(self.GUIDs.Server.New)

    @property
    def Updating(self):
        return len(self.GUIDs.Server.Existing.OutOfDate)

    @property
    def AlreadyUpToDate(self):
        return len(self.GUIDs.Server.Existing.UpToDate)

    @property
    def Success(self):
        return self.Status == EvernoteAPIStatus.Success

    @property
    def IsError(self):
        return self.Status.IsError
    
    @property    
    def Status(self):
        s1 = self.Results.Adding.Status 
        s2 = self.Results.Updating.Status if self.Results.Updating else EvernoteAPIStatus.Uninitialized
        if s1 == EvernoteAPIStatus.RateLimitError or s2 == EvernoteAPIStatus.RateLimitError:
            return EvernoteAPIStatus.RateLimitError
        if s1 == EvernoteAPIStatus.SocketError or s2 == EvernoteAPIStatus.SocketError:
            return EvernoteAPIStatus.SocketError
        if s1.IsError:
            return s1 
        if s2.IsError:
            return s2 
        if s1.IsSuccessful and s2.IsSuccessful:
            return EvernoteAPIStatus.Success
        if s2 == EvernoteAPIStatus.Uninitialized:
            return s1 
        if s1 == EvernoteAPIStatus.Success:
            return s2
        return s1 
        
    @property
    def Summary(self):
        lst = [
            "New Notes (%d)" % self.Adding,
            "Existing Out-Of-Date Notes (%d)" % self.Updating,
            "Existing Up-To-Date Notes (%d)" % self.AlreadyUpToDate
             ]

        return '    > '.join(lst)

    def loadAlreadyUpdated(self, db_guids):
        self.GUIDs.Server.Existing.UpToDate = db_guids
        self.GUIDs.Server.Existing.OutOfDate = set(self.GUIDs.Server.Existing.All) - set(self.GUIDs.Server.Existing.UpToDate)
        
    def processUpdateInPlaceResults(self, results):
        return self.processResults(results, EvernoteImportType.UpdateInPlace)
        
    def processDeleteAndUpdateResults(self, results):
        return self.processResults(results, EvernoteImportType.DeleteAndUpdate)
        
    @property    
    def ResultsSummaryShort(self):
        line = self.Results.Adding.SummaryShort
        if self.Results.Adding.Status.IsError:
            line += " to Anki. Skipping update due to an error (%s)" % self.Results.Adding.Status
        elif not self.Results.Updating:
            line += " to Anki. Updating is disabled"
        else:
            line += " and " + self.Results.Updating.SummaryShort
        return line 
        
    @property
    def ResultsSummary(self):
        delimiter = "<BR>      -"
        delimiter2 = "<BR>          -"        
        summary = '- ' + self.ResultsSummaryShort 
        lines = self.Results.Adding.SummaryLines
        if len(lines)>0:
            summary += delimiter + delimiter2.join(lines)
        if self.Results.Updating:
            lines = self.Results.Updating.SummaryLines
            if len(lines)>0:
                summary += delimiter + delimiter2.join(lines)
        return summary
    
    @property 
    def APICallCount(self):
        return self.Results.Adding.Remote + self.Results.Updating.Remote if self.Results.Updating else 0
    
    def processResults(self, results, importType = None):
        """
        :type results : EvernoteNoteFetcherResults
        :type importType : EvernoteImportType
        """
        if not importType:
            importType = EvernoteImportType.Add
        results.ImportType = importType        
        if importType == EvernoteImportType.Add:
            results.Max = self.Adding
            results.AlreadyUpToDate = 0
            self.Results.Adding = results 
        else:
            results.Max = self.Updating
            results.AlreadyUpToDate = self.AlreadyUpToDate
            self.Results.Updating = results 
        

    def setup(self,anki_note_ids=None):
        if not anki_note_ids:
            anki_note_ids = self.Anki.get_anknotes_note_ids()
        self.GUIDs.Local = self.Anki.get_evernote_guids_from_anki_note_ids(anki_note_ids)

    def __init__(self, anki=None, metadataProgress=None, server_evernote_guids=None, anki_note_ids=None):
        """
        :param anki: Anknotes Main Anki Instance
        :type anki: anknotes.Anki.Anki
        :type metadataProgress: EvernoteMetadataProgress
        :return:
        """
        if not anki:
            return
        self.Anki = anki
        self.setup(anki_note_ids)
        if metadataProgress:
            server_evernote_guids = metadataProgress.Guids
        if server_evernote_guids:
            self.GUIDs.loadNew(server_evernote_guids)
        self.Results.Adding = EvernoteNoteFetcherResults()
        self.Results.Updating = EvernoteNoteFetcherResults()

class EvernoteMetadataProgress:
    Page = 1
    Total = -1
    Current = -1
    UpdateCount = 0
    Status = EvernoteAPIStatus.Uninitialized
    Guids = []
    NotesMetadata = {}
    """
    :type: dict[str, anknotes.evernote.edam.notestore.ttypes.NoteMetadata]
    """    

    @property
    def IsFinished(self):
        return self.Remaining <= 0

    @property
    def List(self):
        return ["Total Notes: %d" % self.Total,
                "Returned Notes: %d" % self.Current,
                "Result Range: %d-%d" % (self.Offset, self.Completed),
                "Remaining Notes: %d" % self.Remaining,
                "Update Count: %d" % self.UpdateCount]

    @property
    def ListPadded(self):
        lst = []
        for val in self.List:
            pad = 20 - len(val)
            padl = int(round(pad/2))
            padr = padl
            if padl + padr > pad: padr -= 1
            val = ' '*padl + val + ' '*padr
            lst.append(val)
        return lst

    @property
    def Summary(self):
        return ' | '.join(self.ListPadded)

    @property
    def Offset(self):
        return (self.Page - 1) * 250

    @property
    def Completed(self):
        return self.Current + self.Offset

    @property
    def Remaining(self):
        return self.Total - self.Completed

    def __init__(self, page=1):
        self.Page = int(page)

    def loadResults(self, result):
        """
        :param result: Result Returned by Evernote API Call to getNoteMetadata
        :type result: anknotes.evernote.edam.notestore.ttypes.NotesMetadataList
        :return:
        """        
        self.Total = int(result.totalNotes)
        self.Current = len(result.notes)
        self.UpdateCount = result.updateCount
        self.Status = EvernoteAPIStatus.Success
        self.Guids = []
        self.NotesMetadata = {}
        for note in result.notes:
            # assert isinstance(note, NoteMetadata)
            self.Guids.append(note.guid)
            self.NotesMetadata[note.guid] = note        