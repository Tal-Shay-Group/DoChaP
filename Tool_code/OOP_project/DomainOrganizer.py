import re
from sqlite3 import connect


class DomainOrganizer:

    def __init__(self):
        self.allDomains = dict()  # keys are id, vals sre tuple combined from Domain object info
        self.internalID = 0
        self.allExt = dict()
        self.allNames = dict()
        self.allCDD = dict()

    def collectDatafromDB(self, dbname='DB_merged.sqlite'):
        con = connect(dbname)
        cur = con.cursor()
        self.internalID = list(cur.execute("SELECT COUNT(*) FROM DomainType"))[0][0]
        cur.execute('SELECT * FROM DomainType')
        for ud in cur.fetchall():
            c_ud = tuple(ud)
            self.allDomains[c_ud[0]] = c_ud[1:]
            self.allNames[c_ud[1]] = c_ud[0]
            for u_ext in c_ud[5:]:
                if u_ext is not None:
                    self.allExt[u_ext] = c_ud[0]
            self.allCDD[c_ud[4]] = c_ud[0]

    def addDomain(self, domain):
        ncdd = None
        ndesc = None
        oname = None
        cdname = None
        currReg = None
        existExt = [None] * 6
        if domain.extID is None:
            return
        if domain.extID is not None and domain.extID not in self.allExt:
            if domain.name not in self.allNames:
                if domain.cdd is None or domain.cdd not in self.allCDD:
                    self.internalID += 1
                    cdname = domain.name
                    oname = domain.name
                    currReg = self.internalID
                    ndesc = domain.note
                    ncdd = domain.cdd
                elif domain.cdd is not None and domain.cdd in self.allCDD:
                    existExt = list(self.allDomains[self.allCDD[domain.cdd]][4:])
                    currReg = self.allCDD[domain.cdd]
                    ndesc = self.noteAdd(domain, currReg)
                    cdname, oname = self.mainNameOtherName(domain, currReg)
                    ncdd = str(self.allDomains[currReg][3])
            elif domain.name in self.allNames:
                existExt = list(self.allDomains[self.allNames[domain.name]][4:])
                currReg = self.allNames[domain.name]
                ncdd = self.cddAdd(domain, currReg)
                ndesc = self.noteAdd(domain, currReg)
                cdname, oname = self.mainNameOtherName(domain, currReg)
        elif domain.extID in self.allExt and domain.extID is not None:
            currReg = self.allExt[domain.extID]
            if domain.name.lower() == self.allDomains[currReg][0].lower() or \
                    domain.name.lower() in self.allDomains[currReg][1].lower():
                ncdd = self.cddAdd(domain, currReg)
                ndesc = self.noteAdd(domain, currReg)
                existExt = self.allDomains[currReg][4:]
                cdname, oname = self.mainNameOtherName(domain, currReg)
            elif re.sub(r'[_ ]\d+$', '', domain.name) == re.sub(r'[_ ]\d+$', '', self.allDomains[currReg][0]):
                ncdd = self.cddAdd(domain, currReg)
                ndesc = self.noteAdd(domain, currReg)
                cdname = re.sub(r'[_ ]\d+$', '', self.allDomains[currReg][0])
                oname = self.allDomains[currReg][1]
                if domain.name.lower() not in self.allDomains[currReg][0].lower() and \
                        domain.name.lower() not in self.allDomains[currReg][1].lower():
                    oname = oname + '; ' + domain.name
                existExt = self.allDomains[currReg][4:]
            else:
                ncdd = self.cddAdd(domain, currReg)
                ndesc = self.noteAdd(domain, currReg)
                existExt = self.allDomains[currReg][4:]
                cdname, oname = self.mainNameOtherName(domain, currReg)
        else:
            raise ValueError(
                'ERROR done: extID: ' + str(domain.extID) + '; Name: ' + str(domain.name) + '; CDD: ' + str(domain.cdd))
        # try:
        external = ['cd', 'cl', 'pfam', 'smart', 'tigr', 'interpro']
        pos = external.index(domain.extType)
        if existExt[pos] is None:
            tempexist = list(existExt).copy()
            tempexist[pos] = domain.extID
            existExt = tuple(tempexist)
        elif domain.extID == existExt[pos]:
            pass
        elif existExt[pos].startswith(re.sub(r'\d+$', '', domain.extID)):
            tempexist = list(existExt).copy()
            tempexist[pos] = existExt[pos] + '; ' + domain.extID
            existExt = tuple(tempexist)
        else:
            raise ValueError('External id type not in correct location!')
        self.allDomains[currReg] = (cdname, oname, ndesc, ncdd,) + tuple(existExt)
        self.allExt[domain.extID] = currReg
        self.allNames[domain.name] = currReg
        self.allCDD[domain.cdd] = currReg
        return currReg

    def mainNameOtherName(self, domain, currReg):
        cdname = self.allDomains[currReg][0]
        oname = self.allDomains[currReg][1]
        if domain.extType == 'cd':
            cdname = domain.name
        elif domain.name.lower() not in self.allDomains[currReg][0].lower() and \
                domain.name.lower() not in self.allDomains[currReg][1].lower():
            oname = self.allDomains[currReg][1] + '; ' + domain.name
        return cdname, oname

    def noteAdd(self, domain, currReg):
        if domain.note is not None and \
                domain.note.lower() not in self.allDomains[currReg][2].lower() and \
                self.allDomains[currReg][2].lower() not in domain.note.lower():
            return self.allDomains[currReg][2] + '; ' + domain.note
        else:
            return self.allDomains[currReg][2]

    def cddAdd(self, domain, currReg):
        if domain.cdd is not None and domain.cdd not in str(self.allDomains[currReg][3]) and \
                domain.cdd not in self.allCDD:
            return str(self.allDomains[currReg][3]) + '; ' + domain.cdd
        else:
            return str(self.allDomains[currReg][3])
