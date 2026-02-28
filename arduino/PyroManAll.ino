

/*

  Zündanlage
  Dr. Ralf Korell
  V 1.3.2.14, 29.12.2015
*/

#include <LiquidCrystal.h>
#include <RCSwitch.h>
#include <SoftwareSerial.h>


// EEprom logik

#include <EEPROM.h>
#include <PyroManEprom.h>


// Init Box
const int BUFSIZE = 15;
const int PYROMAN_BOX_ID_ADDRESS = 10;              // EEPROM Adresse, an der die Box Id steht - PyromanSetStatus.ino
const int PYROMAN_BOX_AUTONOM_MODUS_ADDRESS = 20;   // EEPROM Adresse, an der der AutonomieModus steht - PyromanSetStatus.ino
const int PYROMAN_BOX_NUMBER_OF_STORED_CODES_ADDRESS = 30;  // EEPROM Adresse, an der die Anzahl gspeciherter Fremdwete sthet

char eprombuf[BUFSIZE];  // Buffer zum Beschreiben des EEPROMs
const int PYROMAN_BOX_START_NON_STICKY = 4;

// Counter für die Anzahl gespeicherter Fremdwerte
int epromcounter = PYROMAN_BOX_START_NON_STICKY; 
                         // Wird in der Zählschleife mit zehn multpliziert und definiert damit 
                         // die Adresse des Codes -
                         // startet obderhalb der unveränderlichen Werte (10, 20, 30) daher bei 40)
const int AnzahlCodes = 20;
char cPyroManAktuelleBox[BUFSIZE];   // char buffer for Eprom read
char cPyroManAutonomModus[BUFSIZE];  // char buffer for Eprom read
int hilfscounter = 0;

///////////////
// wird aus dem EEprom gelesen, muss aber hier global initialisiert werden ..
int PyroBox = 0;              // Nummmer der aktuellen Box
boolean BoxAutonom = true;    // entscheidet, ob der arduino selbst die Relais abschaltet: Das ist mit relay verbunden - in diese rZeit ist keine andere Aktion möglich
///////////////


// Prüfen:
const bool DEBUGMODE = true;  // legt fest, ob Zündbefehle im eeprom gespeichert werden und ob die eeprom leseroutine output liefert
const bool CONSOLE_DEBUG = false;
boolean GruppenFeuerGleichzeitig = false;


unsigned long RELAISWARTEZEIT = 2300;   // Wartezeit wenn Box autunom die Relais ausschaltet
int RWZT = RELAISWARTEZEIT / 1000;
int RWZK = (RELAISWARTEZEIT - (RWZT*1000)) / 100;
const int BreakEven = 10;  // Werte höher als Break even sind Abschaltbefehle 
const unsigned long WARTEZEIT = 750;   // Wartezeit für Doppelsendungen
int BOELLERWARTEZEIT = 750;   // Wartezeit zwischen den Einzelschüssen bei Gruppenfuer 

// Initialisierung obligater Variablen:

boolean EEPROMTOERASE = false;  // wenn auf wahr gesetzt, wird der eprom Inhalt gelöscht
unsigned long CurrentValue = 0;  // NImmt beim Lesen der Inputschleife den aktuell gelesenen Wert auf



// Ausnahmen: 
// 9999xxx = Test, letzte Stelle definiert die Boxnummer
// 8000000 - 8001000  Sonderbefehle - z.B. AutonomModus aus/ein , Fremdzündbefehle zeigen, Eeprom Löschen, Gruppenfeuer synchron/asynchron
// 111111 = Alle Aus - not implemented
// 500000 - 6000000 = Handfunksender, HandfunksenderSpannweite - löst nix aus wird aber geloggt ...
// Ausnahmezustand ist die Untergrenze für Ausnahmeziffern, die bei 111111 afangen, alle Anderen sind größer

const unsigned long AusnahmeZustand = 111110;  
const int AusnahmeAnzahl = 5;
//const int AlleAusAusnahme = 0;
const int HandSenderAusnahme = 1;   // Handsender ist default Ausnahme - entspricht im Array Platz 2 = index 1
const int SonderbefehlAusnahme = 2;
const int WartezeitAusnahme = 3;
const int BoxTestAusnahme=4;

const unsigned long AusnahmenStart[] = 
{111111,
5000000,
8000001,
8100001,
9999001};

const unsigned long AusnahmenStop[] = 
{199999,
6000000,
8001000,
8199999,
9999999};
/*
const char* Meldungen[] =
{"Alle aus",
"Funk Handsender",
"Sonderbefehl",
"Wartezeit",
"Test f. Box "};
*/
const char* Meldungen[] =
{"Alle Aus",
"FunkHandsender",
"SonderBefehl",
"Wartezeit",
"Test f. Box"};

// init 433MHz lib
RCSwitch mySwitch = RCSwitch();
unsigned long lOldValue=0;  // to check for consecutive reads on 433MHz


// Die Pins, die die Relais schalten (A-Pins)
const int outpin[] = {0,A0,A1,A2,A3,A4,A5,10,9} ;

// Initialisierung der Display Lib mit den Numern der angeschlossenen Pins 

LiquidCrystal lcd(12, 11, 7, 6, 5, 4);


void setup() 
{

  char buffer[18];
  Serial.begin(9600);
  
  // set-up rf receiver
  mySwitch.enableReceive(0);  // 433MHz Receiver on interrupt 0 => that is pin #2

  // OutPins für Output definieren.
  // und auf HIGH setzen. Das Relais wird verbunden über NO
  // == Normally OPEN. Status "LOW" schaltet das Relais AN !
  for (int count=1;count<9;count++) {
     pinMode(outpin[count], OUTPUT);
   //  pinMode(A0, OUTPUT);
     digitalWrite(outpin[count], HIGH);
  }



///////   Box Nummer und AutonomieModus aus dem EEProm Auslesen:

  eeprom_read_string(PYROMAN_BOX_ID_ADDRESS,cPyroManAktuelleBox,BUFSIZE);
  eeprom_read_string(PYROMAN_BOX_AUTONOM_MODUS_ADDRESS,cPyroManAutonomModus,BUFSIZE);
  
  int testinteger = atoi (cPyroManAktuelleBox);
  Serial.print("Read PyroBox:  " );
  Serial.println(testinteger); 
  // eeprom_serial_dump_table();

  int testinteger2 = atoi (cPyroManAutonomModus);
  PyroBox = atoi(cPyroManAktuelleBox);

  if (testinteger2 == 1) {
       BoxAutonom = true;
       Serial.println("Autonom = true");
     }
  else {
       BoxAutonom = false;
       Serial.println("Autonom = false");
     }


///////
  if (CONSOLE_DEBUG) {
  Serial.print("PyroMan Box - ");
  Serial.print(PyroBox);
  Serial.println("  -  Ralf Korell und Harald Duppich");
  }
  // set up the LCD's number of columns and rows: 
  lcd.begin(16, 2);
  // Print a message to the LCD.

  if (not BoxAutonom){ // Box NICHT autonom  "N" - Relais müssen manuell ausgeschaltet werden
    if (GruppenFeuerGleichzeitig){  // Synchron = "S" 
    sprintf(buffer,"PyroMan  %d N/S    ", PyroBox);
    }
    else { // Gruppenfeuer erfolgt mit Pause
    sprintf(buffer,"PyroMan  %d N/A     ", PyroBox);  // Asynchron "A" 
    } 
  }
  else {  // Box IST autonom - "A"  schaltet die Relais selbständig ab ...
    if (GruppenFeuerGleichzeitig){
    sprintf(buffer,"PyroMan  %d A/S    ", PyroBox);
    }
    else {
    sprintf(buffer,"PyroMan  %d A/A     ", PyroBox);  
    } 
  }      


      
  lcd.setCursor(0, 0);
  lcd.print(buffer);
  lcd.setCursor(0, 1);
  lcd.print("Korell / Duppich");

}  // end setup()

void loop() 
{
  char buf[30];
  int bin_ich_gemeint = 0;
  if (mySwitch.available()) 
  {
    int value = mySwitch.getReceivedValue();

    // only react, if at least two times same value received    
    if (value == lOldValue)
    {
      if (value == 0) 
      {
        if (CONSOLE_DEBUG) Serial.print("Unbekannter Code!");
        lcd.setCursor(0, 1);
        lcd.print("Unbekannter Code!");          
      } 
      else 
      {
        CurrentValue = mySwitch.getReceivedValue();
        if (CONSOLE_DEBUG)  {  
        Serial.print("Gelesen ");
        Serial.println( CurrentValue );
        }
    
        // Prüfroutine, ob die Box gemeint ist.
        // 0 = nicht gemeint,
        // 1 -8 = Feuer auf Einzelkanal,
        // 9 = Gruppenfeuer 1-4
        // 10 = Gruppenfeuer 5-8
        

        boolean fgefunden = false; // Feuerbefehl gefunden
        boolean agefunden = false; // Ausschaltbefehl gefunden
       
        if (CurrentValue < AusnahmeZustand)  //  Normaler Feuerbefehl 
        {

        
        int relais = 0;            // zu schaltendes Relais
        int TempSendBox = int(CurrentValue / 100);  // durch int() wird die Nachkommastelle abgeschnistten
        int TempHunderter = TempSendBox * 100;
        int TempSendKanal = CurrentValue - TempHunderter;  // Hunderter abziehen ergibt den zehner
        int PrintRelais = TempSendKanal;  // relais überlebt die Schleife nicht ??
        if (CONSOLE_DEBUG)  {  
        Serial.print("Box: ");
        Serial.print( TempSendBox );
        Serial.print( "  Kanal: " );
        Serial.println( TempSendKanal );        
        }

        if (TempSendBox == PyroBox)   // Feuer Befehl für Box ...
         {
           
           if (TempSendKanal > BreakEven)  // dies ist ein Abschaltbefehl
           { 
             agefunden = true; // Schleifeneinstieg unten
             relais = TempSendKanal - BreakEven;
             
           }
           else   // dann muss es ein Feuerbefehl sein
           {
             fgefunden = true; // Schleifeneinstieg unten
             relais = TempSendKanal;             
             }
             
         } // end if Feuerbefehl für Box
 
        // LCDlöschen und Status ausgeben...
        lcd.clear();


        if (not BoxAutonom){ // Box NICHT autonom  "N" - Relais müssen manuell ausgeschaltet werden
          if (GruppenFeuerGleichzeitig){  // Synchron = "S" 
          sprintf(buf,"PyroMan  %d N/S    ", PyroBox);
          }
          else { // Gruppenfeuer erfolgt mit Pause
          sprintf(buf,"PyroMan  %d N/A     ", PyroBox);  // Asynchron "A" 
          } 
        }
        else {  // Box IST autonom - "A"  schaltet die Relais selbständig ab ...
          if (GruppenFeuerGleichzeitig){
          sprintf(buf,"PyroMan  %d A/S    ", PyroBox);
          }
          else {
          sprintf(buf,"PyroMan  %d A/A     ", PyroBox);  
          } 
        }      




        lcd.setCursor(0, 0);
        lcd.print(buf);

          // Jetzt wissen wir, ob an- oder ausgeschaltet wird und auf welchem Pin ...
          if (fgefunden == true or agefunden == true)  // es wird etwas geschaltet  ...
          {
             if (CONSOLE_DEBUG)  {  
             Serial.print ("Box ");
             Serial.print (PyroBox);
             Serial.print(" Relais ");}
                        

             if (fgefunden == true)  // Feuer
             {
               if (relais < 9){            
               if (CONSOLE_DEBUG)  {  
               Serial.print (relais) ;       
               Serial.println(" wird gefeuert ...");}
               
               sprintf(buf,"Relais %d  ON", relais);
               digitalWrite(outpin[relais], LOW);  // Relais wir mit LOW eingeschaltet

// --------------------------
               if (DEBUGMODE)
               {

               sprintf(eprombuf,"R%d-%lu", relais, millis() / 1000UL); 
               eeprom_write_string(epromcounter * 10, eprombuf);   // schreibe gefundenen Wert in den Speiher
               if (CONSOLE_DEBUG)  {  
               Serial.print("Empfangener Feuerbefehl ");
               Serial.println(eprombuf);}

               sprintf(eprombuf,"%d", epromcounter - PYROMAN_BOX_START_NON_STICKY +1);  // schreibe den aktuellen counter in eien String
               eeprom_write_string(PYROMAN_BOX_NUMBER_OF_STORED_CODES_ADDRESS, eprombuf); // schreibe dden aktuellen counter in den Speicher 
               if (CONSOLE_DEBUG)  {  
               Serial.print("epromcounter ");
               Serial.println (eprombuf) ;}       
      
               hilfscounter = hilfscounter +1;
               // sprintf(buf,"Addr: %d , n=%d", epromcounter * 10, hilfscounter);         
      
               epromcounter = epromcounter +1;
               if (epromcounter  - PYROMAN_BOX_START_NON_STICKY +1 > AnzahlCodes)
               {
                 epromcounter = PYROMAN_BOX_START_NON_STICKY;
                 sprintf(eprombuf,"%d", AnzahlCodes);  // schreibe den aktuellen counter in eien String
                 eeprom_write_string(PYROMAN_BOX_NUMBER_OF_STORED_CODES_ADDRESS, eprombuf); // schreibe dden aktuellen counter in den Speicher 
                 if (CONSOLE_DEBUG)  Serial.println ("epromcounter reset"); 
               } // end if empromcounter > Anzahl Codes
               } // end if (DEBUGMODE)

//  --------------------------------------


               
               // Für autonomen Modus separate Meldung ausgeben, warten und Relais abschalten
               if (BoxAutonom){

                  sprintf(buf,"Auto: R%d - %d.%ds", relais,RWZT, RWZK );

                  lcd.setCursor(0, 1);
                  lcd.print(buf);
                  delay(RELAISWARTEZEIT);
                  digitalWrite(outpin[relais], HIGH);  // Relais wir mit HIGH abgeschaltet
                  sprintf(buf,"Relais %d OFF    ", relais);
                  lcd.setCursor(0, 1);
                  lcd.print(buf);
                  lcd.setCursor(0, 0);
                  
                 }  // EndIf Boxautonom

               }

               else if (relais == 9){
               if (CONSOLE_DEBUG)  Serial.println(" Gruppe 1 wird gefeuert ...");
               sprintf(buf,"%d - GRUP 1 ON", relais);
               lcd.setCursor(0, 1);
               lcd.print(buf);
               
               for (int trel=1;trel<5;trel++)  //temporärer relaiszähler - Gruppenschaltung 1 - 4
                 {
                   digitalWrite(outpin[trel], LOW);  // Relais wir mit LOW eingeschaltet
                   if (not GruppenFeuerGleichzeitig) 
                   { 
                      
                      sprintf(buf,"Relais %d -  ON", trel);
                      lcd.setCursor(0, 1);
                      lcd.print(buf);
                      if (trel <4) {delay(BOELLERWARTEZEIT);}
                     
                   }  // EndIF Gruppenfeuer nicht gleichzeitig ...
                 }

 
 // --------------------------
               if (DEBUGMODE)
               {
               sprintf(eprombuf,"G1-%lu", millis() / 1000UL); 
               eeprom_write_string(epromcounter * 10, eprombuf);   // schreibe gefundenen Wert in den Speiher

               if (CONSOLE_DEBUG)  {  
               Serial.print("Empfangener Feuerbefehl ");
               Serial.println(eprombuf);}

               sprintf(eprombuf,"%d", epromcounter - PYROMAN_BOX_START_NON_STICKY +1);  // schreibe den aktuellen counter in eien String
               eeprom_write_string(PYROMAN_BOX_NUMBER_OF_STORED_CODES_ADDRESS, eprombuf); // schreibe dden aktuellen counter in den Speicher 

               if (CONSOLE_DEBUG)  {  
               Serial.print("epromcounter ");
               Serial.println (eprombuf) ;}       
      
               hilfscounter = hilfscounter +1;
               // sprintf(buf,"Addr: %d , n=%d", epromcounter * 10, hilfscounter);         
      
               epromcounter = epromcounter +1;
               if (epromcounter  - PYROMAN_BOX_START_NON_STICKY +1 > AnzahlCodes)
               {
                 epromcounter = PYROMAN_BOX_START_NON_STICKY;
                 sprintf(eprombuf,"%d", AnzahlCodes);  // schreibe den aktuellen counter in eien String
                 eeprom_write_string(PYROMAN_BOX_NUMBER_OF_STORED_CODES_ADDRESS, eprombuf); // schreibe dden aktuellen counter in den Speicher 
                 if (CONSOLE_DEBUG)  Serial.println ("epromcounter reset"); 
                
               } // end if empromcounter > Anzahl Codes
               } // END if (DEBUGMODE)


//  --------------------------------------

               // Für autonomen Modus separate Meldung ausgeben, warten und Relais abschalten
               if (BoxAutonom){
                  sprintf(buf,"Auto: G1-4 %d.%ds", RWZT, RWZK );
                  lcd.setCursor(0, 1);
                  lcd.print(buf);
                  delay(RELAISWARTEZEIT);
                  for (int trel=1;trel<5;trel++)  //temporärer relaiszähler - Gruppenschaltung 1 - 4
                    {
                      digitalWrite(outpin[trel], HIGH);  // Relais wir mit HIGH ausgeschaltet
                    }

                  sprintf(buf,"Gruppe 1 - 4 OFF");
                  lcd.setCursor(0, 1);
                  lcd.print(buf);
                 }  // EndIf Boxautonom

               } // end if relais = 9
               
               else if (relais == 10){
               if (CONSOLE_DEBUG)  {  
               Serial.println(" Gruppe 2 wird gefeuert ...");
               sprintf(buf,"%d - GRUP 2 ON", relais);}
               for (int trel=5;trel<9;trel++)  //temporärer relaiszähler - Gruppenschaltung 5 - 8
                 {
                   digitalWrite(outpin[trel], LOW);  // Relais wir mit LOW eingeschaltet
                   if (not GruppenFeuerGleichzeitig) 
                   { 
                      
                      sprintf(buf,"Relais %d -  ON", trel);
                      lcd.setCursor(0, 1);
                      lcd.print(buf);
                      if (trel <8) {delay(BOELLERWARTEZEIT);}
                     
                   }  // EndIF Gruppenfeuer nicht gleichzeitig ...

                 }     // end for loop 5-8          

 // --------------------------
               if (DEBUGMODE)
               {

               sprintf(eprombuf,"G2-%lu", millis() / 1000UL); 
               eeprom_write_string(epromcounter * 10, eprombuf);   // schreibe gefundenen Wert in den Speicher

               if (CONSOLE_DEBUG)  {  
               Serial.print("Empfangener Feuerbefehl ");
               Serial.println(eprombuf);}
               
               sprintf(eprombuf,"%d", epromcounter - PYROMAN_BOX_START_NON_STICKY +1);  // schreibe den aktuellen counter in eien String
               eeprom_write_string(PYROMAN_BOX_NUMBER_OF_STORED_CODES_ADDRESS, eprombuf); // schreibe dden aktuellen counter in den Speicher 

               if (CONSOLE_DEBUG)  {  
               Serial.print("epromcount ");
               Serial.println (eprombuf) ;}       
      
               hilfscounter = hilfscounter +1;
               // sprintf(buf,"Addr: %d , n=%d", epromcounter * 10, hilfscounter);         
      
               epromcounter = epromcounter +1;
               if (epromcounter  - PYROMAN_BOX_START_NON_STICKY +1 > AnzahlCodes)
               {
                 epromcounter = PYROMAN_BOX_START_NON_STICKY;
                 sprintf(eprombuf,"%d", AnzahlCodes);  // schreibe den aktuellen counter in eien String
                 eeprom_write_string(PYROMAN_BOX_NUMBER_OF_STORED_CODES_ADDRESS, eprombuf); // schreibe dden aktuellen counter in den Speicher 
                 if (CONSOLE_DEBUG)  Serial.println ("epromcounter reset"); 
                
               } // end if empromcounter > Anzahl Codes
               } // END if (DEBUGMODE)

//  --------------------------------------


               // Für autonomen Modus separate Meldung ausgeben, warten und Relais abschalten
               if (BoxAutonom){
                  sprintf(buf,"Auto: G5-9 %d.%ds", RWZT, RWZK );
                  lcd.setCursor(0, 1);
                  lcd.print(buf);
                  delay(RELAISWARTEZEIT);
                  for (int trel=5;trel<9;trel++)  //temporärer relaiszähler - Gruppenschaltung 1 - 4
                    {
                      digitalWrite(outpin[trel], HIGH);  // Relais wir mit HIGH ausgeschaltet
                    }

                  sprintf(buf,"Gruppe 5 - 8 OFF");
                  lcd.setCursor(0, 1);
                  lcd.print(buf);
                 }  // EndIf Boxautonom

               } // end if relais = 10
 
             } // endif fgefunden
             else if (agefunden == true)  // Abschaltbefehl
             {
               if (relais < 9){            
               if (CONSOLE_DEBUG)  {  
               Serial.print (relais) ;       
               Serial.println(" wird abgeschaltet ..."); }
               sprintf(buf,"Relais %d  OFF", relais);               
               digitalWrite(outpin[relais], HIGH);  // Relais wir mit HIGH abgeschaltet
                 
             }
               else if (relais == 9){
               if (CONSOLE_DEBUG)  Serial.println(" Gruppe 1 wird abgeschaltet ...");
               sprintf(buf,"%d - GRUP 1 OFF", relais);
               for (int trel=1;trel<5;trel++)  //temporärer relaiszähler - Gruppenschaltung 1 - 4
                 {
                   digitalWrite(outpin[trel], HIGH);  // Relais wir mit HIGH ausgeschaltet
                   }               
               }
               else if (relais == 10){
               if (CONSOLE_DEBUG)  Serial.println(" Gruppe 2 wird abgeschaltet ...");
               sprintf(buf,"%d - GRUP 2  OFF", relais);
               for (int trel=5;trel<9;trel++)  //temporärer relaiszähler - Gruppenschaltung 1 - 4
                 {
                   digitalWrite(outpin[trel], HIGH);  // Relais wird mit HIGH ausgeschaltet
                   }               
               }
               
             } // end if agefunden
             
          }  // endif fgefunden or agefunden
          
          else  // kein Feuer- und kein Abschaltbefehl
          {
             if (CONSOLE_DEBUG)  {  
             Serial.print ("Box  ");
             Serial.print (PyroBox);
             Serial.print (" Relais ");
             Serial.print (PrintRelais);
             Serial.println ("  ist NICHT gemeint ...");}       
             sprintf(buf,"B%d - R%d: N/A", TempSendBox, PrintRelais);              
          }

        lcd.setCursor(0, 1);
        lcd.print(buf);
        
        // Warten, um Doppelmeldungen zu vermeiden  ...
        
        if (not BoxAutonom){  // Wenn die Box autonom arbeitet, wartet si sowie, um abzuschalten ..
          delay(WARTEZEIT);
        }
       } // end if Normaler Feuebefehl

//  -------------------


      else if (CurrentValue > AusnahmeZustand)  // Ausnahmezustand - KEIN Normaler Feuerbefehl 
      {
         
        int AktuelleAusnahme = HandSenderAusnahme;  // Default auf Handsender
        lcd.clear();
        for (int count=0;count<AusnahmeAnzahl;count++) {
         if (CurrentValue >= AusnahmenStart[count] and  CurrentValue <= AusnahmenStop[count]) {
            AktuelleAusnahme = count; 
            } // end if 
             
        } // end for

        sprintf(buf,"Ausnahme ...");
        lcd.setCursor(0, 0);
        lcd.print(buf);
        lcd.setCursor(0, 1);
        lcd.print(Meldungen[AktuelleAusnahme]);
        
        // Hier jetzt je nach Ausnahme unterschiedlich agieren  ...
            // AlleAusAusnahme = 0      - im Moment unbenutzt und daher nicht implementiert.
            // HandSenderAusnahme = 1   - Hier hat jemenad quer gefeurt  -- nicht reagieren, 
            //                            aber den code im EEprom ablegen, damit hinterher ein logging möglich ist ... 
            // Sonderbefehlausnahme = 2  
            // Wartezeitausnahme = 3
            // BoxTestAusnahme = 4 
            
        
        if (AktuelleAusnahme == SonderbefehlAusnahme)
        {
          int Sonderbefehl = CurrentValue - 8000000;
          
          delay(800);
          lcd.clear();

          // sprintf(buf,"Test:  Box %d" , AngefragteBox);         
          lcd.setCursor(0, 0);
          sprintf(buf, "SB: %d           ", Sonderbefehl);
          lcd.print(buf);  

          if (CONSOLE_DEBUG)  {
          sprintf(buf, "CurrentVAlue %lu  Sonderbefehl: %d           ", CurrentValue, Sonderbefehl);
          Serial.println (buf);}  

            if (Sonderbefehl == 10){ // AutonomModus OFF
              lcd.setCursor(0, 1);
              lcd.print("Auto Mode:  OFF " ); 
              BoxAutonom = false; 
              } // endif 10 
              
            else if (Sonderbefehl == 11){ // AutonomModus ON
              lcd.setCursor(0, 1);
              lcd.print("Auto Mode:  ON " );  
              BoxAutonom = true;
              }   // endif 11

            else if (Sonderbefehl == 21){    // Gespeicherte EEprom Werte auslesen - dort werden die Feuerbefehle
                                             // Also z.B. Handsender Codes o.ä. 
              if (DEBUGMODE)
              {
              eeprom_read_string(PYROMAN_BOX_NUMBER_OF_STORED_CODES_ADDRESS, eprombuf, BUFSIZE);
              int testinteger = atoi(eprombuf);
              lcd.setCursor(0, 0);
              if (testinteger > 0){
                sprintf (buf, "Lese %d Werte:      ", testinteger);
                lcd.print(buf); 
                lcd.setCursor(0, 1);
                for  (int ii=PYROMAN_BOX_START_NON_STICKY ;ii<testinteger +PYROMAN_BOX_START_NON_STICKY;ii++)
                 {
                    eeprom_read_string(ii*10, eprombuf, BUFSIZE);
                    if (CONSOLE_DEBUG)   {   
                    Serial.println("Reading string from eeprom...");
                    Serial.print("String read: '");
                    Serial.print(eprombuf);
                    Serial.println("'");}
                    
                    lcd.setCursor(0, 1);
                    // sprintf(buf, "%d: %s ", ii - PYROMAN_BOX_START_NON_STICKY +1, eprombuf);
                    sprintf(buf, "%s", eprombuf);
                    lcd.print(buf);
                    delay(RELAISWARTEZEIT);
                 }
 

                }  // endif testinteger > 0 -- Werte gefunden ...
                else {
                  lcd.setCursor(0, 0);
                  lcd.print("Lese EEProm:"); 
                  lcd.setCursor(0, 1);
                  lcd.print("Keine Werte..."); 
                }
                } // END if (DEBUGMODE)
                else // NO Debug Mode
                { 
                  lcd.setCursor(0, 0);
                  lcd.print("DEBUG is OFF"); 

                }
                


              } // endif 21

            else if (Sonderbefehl == 22){ // DELETE EEPROM   ...
              lcd.setCursor(0, 0);
              lcd.print("DELETING EEProm ..." );  
              
              if (CONSOLE_DEBUG)   {   
              Serial.println("DELETING EEprom Values");
              Serial.println("Dumping eeprom contents before deletetion  --- ");
              eeprom_serial_dump_table();}
              
              eeprom_erase_all();
              
              sprintf(eprombuf,"%d", 0);  // schreibe den aktuellen counter in eien String
              eeprom_write_string(PYROMAN_BOX_NUMBER_OF_STORED_CODES_ADDRESS, eprombuf); // schreibe dden aktuellen counter in den Speicher 

              lcd.setCursor(0, 1);
              lcd.print("Done  ...           " );  
              

              }   // endif 22
           
            else if (Sonderbefehl == 31){ // Gruppenbefehl Asynchron (mit Pause)   ...
              lcd.setCursor(0, 0);
              lcd.print("Groups Asynchron" );  
              if (CONSOLE_DEBUG)   Serial.println("Gruppenfeuer mit Pause");
              GruppenFeuerGleichzeitig = false;

              }   // endif 31
            
            else if (Sonderbefehl == 32){ // Gruppenbefehl Synchron (Ohne Pause)   ...
              lcd.setCursor(0, 0);
              lcd.print("Groups Synchron" );  
              if (CONSOLE_DEBUG)   Serial.println("Gruppenfeuer ohne Pause");
              GruppenFeuerGleichzeitig = true;

              }   // endif 31

        } // end elsif Sonderbefehlausnahme


        else if (AktuelleAusnahme == WartezeitAusnahme)
        {
          lcd.clear();
          sprintf(buf,"WZ alt: %d" , BOELLERWARTEZEIT);         
          lcd.setCursor(0, 0);
          lcd.print(buf);  
          BOELLERWARTEZEIT = CurrentValue - 8100000;

          sprintf(buf,"WZ neu: %d" , BOELLERWARTEZEIT);         
          lcd.setCursor(0, 1);
          lcd.print(buf);  
          
        } // end elsif Wartezeitausnahme
        
        else if (AktuelleAusnahme == BoxTestAusnahme)
        {
          lcd.clear();
          int AngefragteBox = CurrentValue - 9999000;

          sprintf(buf,"Test:  Box %d" , AngefragteBox);         
          lcd.setCursor(0, 0);
          lcd.print(buf);  
          
          if (AngefragteBox == PyroBox){
             sprintf(buf,"Lege los ...." );         
             lcd.setCursor(0, 1);
             lcd.print(buf);  
             int warten = 500;

             delay(warten);
             for (int trel=1;trel<9;trel++)  {
                   sprintf(buf,"Relais %d ein" , trel);         
                   delay(warten);
                   lcd.setCursor(0, 1);
                   lcd.print(buf);  
                   digitalWrite(outpin[trel], LOW);  // Relais wir mit LOW ausgeschaltet
                   delay(warten); 
                    }   // end for  

             delay(warten);
             for (int trel=1;trel<9;trel++)  {
                   sprintf(buf,"Relais %d aus" , trel);         
                   delay(warten);
                   lcd.setCursor(0, 1);
                   lcd.print(buf);  
                   digitalWrite(outpin[trel], HIGH);  // Relais wir mit HIGH eingeschaltet
                   delay(warten); 
                    }   // end for  

                 
            } // endif angrfragte Box = Pyrobox

          else{
            sprintf(buf,"Ich bin Box %d" , PyroBox);         
            lcd.setCursor(0, 1);
            lcd.print(buf);  
            } // end else Angefragte Box <> Pyrobox
            
           
          } // endif BoxTextAusnahme
          // LCDlöschen und Status ausgeben...
          delay(2500);
          lcd.clear();
          if (not BoxAutonom){ // Box NICHT autonom  "N" - Relais müssen manuell ausgeschaltet werden
            if (GruppenFeuerGleichzeitig){  // Synchron = "S" 
            sprintf(buf,"PyroMan  %d N/S    ", PyroBox);
            }
            else { // Gruppenfeuer erfolgt mit Pause
            sprintf(buf,"PyroMan  %d N/A     ", PyroBox);  // Asynchron "A" 
            } 
          }
          else {  // Box IST autonom - "A"  schaltet die Relais selbständig ab ...
            if (GruppenFeuerGleichzeitig){
            sprintf(buf,"PyroMan  %d A/S    ", PyroBox);
            }
            else {
            sprintf(buf,"PyroMan  %d A/A     ", PyroBox);  
            } 
          }      
          lcd.setCursor(0, 0);
          lcd.print(buf);
          lcd.setCursor(0, 1);
          lcd.print("Korell/Duppich");

       } // end elsif Ausnahmezustand


      }      // end els code <> 0
    } //  endif lOldValue = value
    lOldValue = value;
    mySwitch.resetAvailable();  
  }// my Switch available

} // 
