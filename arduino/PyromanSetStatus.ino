/*

  EEprom DauerVariablen für PyroMan Boxen in das Arduino EEprom schreiben
  
  Dr. Ralf Korell

*/

#include <LiquidCrystal.h>
#include <RCSwitch.h> 
#include <SoftwareSerial.h>

#include <EEPROM.h>
#include <PyroManEprom.h>

////////////////////////////
// ANPASSEN :
int nPyroBox = 9;          
int nBoxAutonom = 1;
////////////////////////////

int nAnzahlCodes= 0;


const int PYROMAN_BOX_ID_ADDRESS = 10;      // EEPROM Adresse, an der die Box Id steht - PyromanSetStatus.ino
const int PYROMAN_BOX_AUTONOM_MODUS_ADDRESS = 20;   // EEPROM Adresse, an der der AutonomieModus steht - PyromanSetStatus.ino
const int PYROMAN_BOX_NUMBER_OF_STORED_CODES_ADDRESS = 30;  // EEPROM Adresse, an der die Anzahl gspeciherter Fremdwete sthet
const int BUFSIZE = 50;

char PyroManAktuelleBox[BUFSIZE];
char PyroManAutonomModus[BUFSIZE];
char PyroManNumberOfStoredCodes[BUFSIZE];

// Char Zwischenpuffer  ..

char cPyroManAktuelleBox[BUFSIZE];
char cPyroManAutonomModus[BUFSIZE];
char cPyroManNumberOfStoredCodes[BUFSIZE];


int PyroBox = 0;          
boolean BoxAutonom = false;
char buffer[BUFSIZE];

LiquidCrystal lcd(12, 11, 7, 6, 5, 4);

void setup ()
{
  Serial.begin(9600);
  lcd.begin(16, 2);
  sprintf(PyroManAktuelleBox,"%d", nPyroBox); 
  sprintf(PyroManAutonomModus,"%d", nBoxAutonom); 
  sprintf(PyroManNumberOfStoredCodes,"%d", nAnzahlCodes); 
  
  lcd.setCursor(0, 0);
  lcd.print("P.M.: EepromBurn");
  lcd.setCursor(0, 1);
  lcd.print("Delete NonSticky");
  eeprom_erase_all();
  
  sprintf(buffer,"W: B: %s /A: %s     ", PyroManAktuelleBox, PyroManAutonomModus); 
  lcd.setCursor(0, 1);
  lcd.print(buffer);
   
  eeprom_write_string(PYROMAN_BOX_ID_ADDRESS,PyroManAktuelleBox);
  eeprom_write_string(PYROMAN_BOX_AUTONOM_MODUS_ADDRESS,PyroManAutonomModus);
  eeprom_write_string(PYROMAN_BOX_NUMBER_OF_STORED_CODES_ADDRESS,PyroManNumberOfStoredCodes);

  eeprom_read_string(PYROMAN_BOX_ID_ADDRESS,cPyroManAktuelleBox,BUFSIZE);
  eeprom_read_string(PYROMAN_BOX_AUTONOM_MODUS_ADDRESS,cPyroManAutonomModus,BUFSIZE);
  delay(5000);
  PyroBox = atoi(cPyroManAktuelleBox);
  int testinteger2 = atoi(cPyroManAutonomModus);
  Serial.println(testinteger2);  
  if (testinteger2 == 1) {
      BoxAutonom = true;
      sprintf(buffer, "R: Box %d/A=j   ", PyroBox  );
    }   
    else {
      BoxAutonom = false;
      sprintf(buffer, "R: Box %d/A=n   ", PyroBox  );
    }

   lcd.setCursor(0, 1);
   lcd.print(buffer);   

   Serial.println(buffer);
   
   Serial.println("Dumping eeprom contents...");
   eeprom_serial_dump_table();
  
   Serial.println(buffer);
   
} // end setup





//
 // LOOP
 //
 void loop() {
  
 }

