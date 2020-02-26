import re


class DomainOrganizer:

    def __init__(self):
        self.allDomains = dict()  # keys are id, vals sre tuple combined from Domain object info
        self.internalID = 0
        self.allExt = dict()
        self.allNames = dict()
        self.allCDD = dict()

    def addDomain(self, domain):
        ncdd = None
        ndesc = None
        oname = None
        cdname = None
        currReg = None
        existExt = [None] * 6
        if domain.extID is not None and domain.extID not in self.allExt:
            # print('extID not  exist')
            if domain.name not in self.allNames:
                # print('name exist 1')
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
                # print('name exist 2')
                existExt = list(self.allDomains[self.allNames[domain.name]][4:])
                currReg = self.allNames[domain.name]
                ncdd = self.cddAdd(domain, currReg)
                ndesc = self.noteAdd(domain, currReg)
                cdname, oname = self.mainNameOtherName(domain, currReg)
        elif domain.extID in self.allExt and domain.extID is not None:
            # print('extID exist')
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
                # print('here 6')
                ncdd = self.cddAdd(domain, currReg)
                ndesc = self.noteAdd(domain, currReg)
                existExt = self.allDomains[currReg][4:]
                cdname, oname = self.mainNameOtherName(domain, currReg)
                # self.allDomains[self.allExt[currExt]] = (self.allDomains[self.allExt[currExt]][0], ndesc, ncdd,) + extIDs
        else:
            raise ValueError('ERROR done: domain: ' + str(domain))
        try:
            external = ['cd', 'cl', 'pfam', 'smart', 'tigr', 'interpro']
            pos = external.index(domain.extType)
            if existExt[pos] is None or domain.extID is existExt[pos]:
                existExt[pos] = domain.extID
            elif existExt[pos].startswith(re.sub(r'\d+$', '', domain.extID)):
                existExt[pos] = existExt[pos] + '; ' + domain.extID
            else:
                raise ValueError('External id type not in correct location!')
            self.allDomains[currReg] = (cdname, oname, ndesc, ncdd,) + tuple(existExt)
            self.allExt[domain.extID] = currReg
            self.allNames[domain.name] = currReg
            self.allCDD[domain.cdd] = currReg
        except Exception:
            raise Exception(str(domain))

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
