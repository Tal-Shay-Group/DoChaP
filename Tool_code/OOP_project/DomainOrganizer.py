import re
from sqlite3 import connect
from Director import Director
from InterproCollector import InterProBuilder
import pandas as pd


class DomainOrganizer:

    def __init__(self, download=False):
        self.allDomains = dict()  # keys are id, vals sre tuple combined from Domain object info
        self.internalID = 0
        self.allExt = dict()
        self.allNames = dict()
        self.allCDD = dict()
        director = Director()
        self.Interpro = InterProBuilder()
        director.setBuilder(self.Interpro)
        director.collectFromSource(download=False)

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
        existExt = [None] * 5
        external = ['cdd', 'pfam', 'smart', 'tigr', 'interpro']
        if domain.extID is None:
            return None
        elif domain.extType not in external:
            return None
        identify = self.Interpro.AllDomains.loc[
            self.Interpro.AllDomains[domain.extType].str.contains(domain.extID, na=False)]
        ind = identify.index.values[0] if len(identify) != 0 else None
        if domain.extID in self.allExt or ind in self.allExt:
            currReg = self.allExt.get(domain.extID if domain.extID is not None else ind, self.allExt.get(ind))
            ncdd = self.cddAdd(domain, currReg)
            ndesc = self.noteAdd(domain, currReg)
            existExt = self.allDomains[currReg][4:]
            cdname, oname = self.mainNameOtherName(domain, currReg)
        else:
            if domain.cdd is not None and domain.cdd in self.allCDD:
                existExt = list(self.allDomains[self.allCDD[domain.cdd]][4:])
                currReg = self.allCDD[domain.cdd]
                ndesc = self.noteAdd(domain, currReg)
                cdname, oname = self.mainNameOtherName(domain, currReg)
                ncdd = str(self.allDomains[currReg][3])
            else:
                self.internalID += 1
                cdname = domain.name
                oname = domain.name
                currReg = self.internalID
                ndesc = domain.note
                ncdd = domain.cdd
        # else:
        #     raise ValueError(
        #         'ERROR done: extID: ' + str(domain.extID) + '; Name: ' + str(domain.name) + '; CDD: ' + str(domain.cdd))
        if ind is not None and ind not in self.allExt:
            Alltypes = ["cdd", "pfam", "smart", "tigrfams", "interpro"]
            indExt = [identify["cdd"][0], identify["pfam"][0], identify["smart"][0],identify['tigrfams'][0], ind]
            indExt = [None if pd.isna(i) else i for i in indExt]
            existExt = map(self.addToExtID, existExt, indExt)
            self.allExt[ind] = currReg
        pos = external.index(domain.extType)
        existExt[pos] = self.addToExtID(domain.extID, existExt[pos])
        # if existExt[pos] is None:
        #     tempexist = list(existExt).copy()
        #     tempexist[pos] = domain.extID
        #     existExt = tuple(tempexist)
        # elif domain.extID in existExt[pos].split("; "):
        #     pass
        # elif existExt[pos].startswith(re.sub(r'\d+$', '', domain.extID)) or \
        #         (domain.extID[0:2] == "cl" and pos == 0):
        #     tempexist = list(existExt).copy()
        #     tempexist[pos] = existExt[pos] + '; ' + domain.extID
        #     existExt = tuple(tempexist)
        if not (existExt[pos].startswith(re.sub(r'\d+$', '', domain.extID)) or \
                (domain.extID[0:2] == "cl" and pos == 0)):
            raise ValueError('External id type not in correct location!')
        self.allDomains[currReg] = (cdname, oname, ndesc, ncdd,) + tuple(existExt)
        self.allExt[domain.extID] = currReg
        self.allNames[domain.name] = currReg
        self.allCDD[domain.cdd] = currReg
        return currReg

    def mainNameOtherName(self, domain, currReg):
        cdname = self.allDomains[currReg][0]
        oname = self.allDomains[currReg][1]
        if domain.extType == 'interpro':
            cdname = domain.name
        elif domain.name is not None:
            if self.allDomains[currReg][0] and self.allDomains[currReg][1] is not None:
                if domain.name.lower() not in self.allDomains[currReg][0].lower() and \
                        domain.name.lower() not in self.allDomains[currReg][1].lower():
                    oname = self.allDomains[currReg][1] + '; ' + domain.name
                else:
                    oname = self.allDomains[currReg][1]
            else:
                oname = domain.name
        return cdname, oname

    def noteAdd(self, domain, currReg):
        if domain.note is not None:
            if self.allDomains[currReg][2] is None:
                return domain.note
            elif domain.note.lower() not in self.allDomains[currReg][2].lower() and \
                    self.allDomains[currReg][2] is not None:
                return self.allDomains[currReg][2] + '; ' + domain.note
            elif self.allDomains[currReg][2].lower() in domain.note.lower():
                return domain.note
            else:
                return self.allDomains[currReg][2]
        else:
            return self.allDomains[currReg][2]

    def cddAdd(self, domain, currReg):
        if domain.cdd is not None and domain.cdd not in str(self.allDomains[currReg][3]) and \
                domain.cdd not in self.allCDD:
            return str(self.allDomains[currReg][3]) + '; ' + domain.cdd
        else:
            return str(self.allDomains[currReg][3])

    def addToExtID(self, extID, currentExt):
        if currentExt is None:
            return extID
        elif extID is None:
            return currentExt
        else:
            return "; ".join(list(set(currentExt.split("; ") + extID.split("; "))))