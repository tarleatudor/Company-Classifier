# Insurance Company Classifier – Veridion Challenge

## Despre task

Scopul acestui proiect este clasificarea unor companii intr-o taxonomie statica din domeniul asigurarilor, folosind informatiile disponibile despre fiecare companie:

- description  
- business tags  
- sector / category / niche  

Nu exista un set de raspunsuri corecte (ground truth), asa ca accentul cade pe modul de gandire.

---

## Cum am abordat problema ?

Inainte sa scriu cod, am incercat sa inteleg ce se cere de fapt:

- Taxonomia este fixa  
- Unele companii sunt clare, altele sunt ambigue  
- O clasificare gresita este mai rea decat lipsa unei clasificari  

Din acest motiv, nu am pornit de la ideea „ce algoritm folosesc”, ci de la cum iau o decizie corecta cu informatiile pe care le am.

---

## De ce NU am folosit modele complexe

Am luat in calcul:

- embeddings  
- zero-shot classification  
- TF-IDF / clustering  

Am renuntat la ele din cateva motive simple:

- Fara ground truth, scorurile obtinute nu demonstreaza corectitudine reala  
- Modelele semantice tind sa fie prea permisive si sa returneze label-uri care par corecte dar sunt gresite  
- Deciziile devin greu de explicat sau corectat  

Pentru un domeniu ca asigurarile, explicabilitatea este mai importanta decat complexitatea.

---

## Solutia aleasa

In acest context, am ales o solutie simpla, controlabila si explicabila, o abordare rule-based, bazata pe dovezi concrete extrase din datele companiei.

Pentru fiecare label din taxonomie caut:

- potriviri in business tags (cea mai mare "greutate")  
- potriviri in category / niche  
- potriviri in description (cea mai mica "greutate")  

Fiecare potrivire adauga un scor.  
Un label este atribuit doar daca scorul depaseste un prag minim. (toate pragurile/valorile globale pot fi adaptate (marite/micsorate) dupa nevoi)

---

## Probleme intalnite si cum le-am rezolvat

### 1. Prea multe label-uri atribuite

La inceput, aproape fiecare companie primea mai multe label-uri.

**Cauze:**
- cuvinte foarte generale (services, management, systems)  
- potriviri pe fragmente de cuvinte (ex: „ice” din „practice”)  

**Solutii:**
- lista de stop-words  
- lungime minima pentru keyword-uri  
- matching doar pe cuvinte intregi  

---

### 2. False positives

Unele companii erau fortate intr-un label desi nu exista suficiente dovezi reale.

**Solutie:**
- preferinta pentru Unclear in lipsa dovezilor  
- limitare la maximum 3 label-uri per companie  

---

### 3. Lipsa transparentei

Nu este suficient sa spui ce label a fost ales, ci si de ce.

**Solutie:**
- pentru fiecare label returnez motivele exacte  
- indic unde a fost gasit keyword-ul  
- adaug un nivel de incredere (low / medium / high)  

Am hotarat sa fac acest lucru intr-un fisier separat pentru a nu altera scopul cerintei (o singura coloana suplimentara).

---

## Output

Sunt generate doua fisiere:

### 1. Output oficial
Contine exact lista initiala de companii + coloana `insurance_label`

### 2. Output cu reasoning
Contine, in plus:
- insurance_reason  
- insurance_confidence  

Acest fisier este util pentru analiza, debug si imbunatatiri ulterioare. De asemenea, a fost foarte util pentru mine pentru a vedea cum functioneaza programul, de ce asociaza gresit, de ce are un sentiment de siguranta daca raspunsul pare sa fie gresit etc.

---

## Scalabilitate

Procesarea se face in chunk-uri (se pot modifica dimensiunile usor).

Poate rula pe volume mult mai mari de date fara modificari majore.

Desi dataset-ul actual este mic, solutia este gandita sa nu depinda de dimensiunea lui.

---

## Limitari asumate

- Taxonomia este tratata ca flat (fara ierarhii)  
- Unele companii sunt inerent ambigue (aici s-a preferat Unclear decat o incadrare nepotrivita)  

Nefolosind tehnici avansate de ML sau modele antrenate, rezultatele nu sunt spectaculoase ca forma,  
dar sunt stabile, explicabile si usor de imbunatatit incremental.

---

## Imbunatatiri posibile

### 1. Imbunatatirea reprezentarii taxonomiei
Daca taxonomia ar contine relatii intre label-uri (de tip parinte–copil), clasificarea ar putea deveni mai precisa.  
De exemplu, un label general ar putea sustine unul mai specific, fara a-l forta.

### 2. Scoruri mai bine calibrate
In prezent, scorurile sunt bazate pe reguli simple.  
In timp, acestea ar putea fi calibrate pe seturi mici de date verificate manual, fara a fi nevoie de un model antrenat complet.

### 3. Context mai bun in descrieri
Matching-ul este facut la nivel de cuvinte, nu de sens.  
O imbunatatire naturala ar fi folosirea de sinonime sau expresii echivalente, pastrand insa controlul asupra deciziilor luate.

### 4. Validare mai structurata
Chiar si fara ground truth, se pot crea seturi mici de companii etichetate manual pentru a testa consistenta si stabilitatea rezultatelor.

---

## Concluzie

Scopul acestei solutii nu a fost sa impresioneze prin complexitate, ci sa rezolve cat se poate de corect problema de baza.

Odata ce logica este solida si explicabila, adaugarea de tehnici si validari doar va imbunatatii modelul.
