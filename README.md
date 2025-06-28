Pasii pentru instalare

-----------------------------------------------------------------------------
1. Aplicația Python

Deschide un terminal (Command Prompt / PowerShell / Terminal / Git Bash) și rulează comanda:

	git clone https://github.com/DLC07/Licenta_Lupei_Dacian.git
	
După clonare, intră în directorul proiectului:

	cd Scripturi_Licenta_Lupei_Dacian\Aplicatie_de_control

Crearea și activarea unui mediu virtual

	Linux/macOS:
	python3 -m venv venv
	source venv/bin/activate

	Windows:
	python -m venv venv
	venv\Scripts\activate

Instalarea dependențelor

	pip install -r requirements.txt

Rularea aplicației

	python app.py
-----------------------------------------------------------------------------

-----------------------------------------------------------------------------
2. Aplicatie Raspberry PI

Scriptul de pe Raspberry poate fi activat in doua moduri:

	i). scriptul se deschide la startup odată cu alimentarea raspberry-ului
	ii). scriptul se mai poate accesa rulând aplicația Thonny prezenta pe Raspberry
	
Pentru scenariu ii). avem următoarea configurare:

	- Se clonează script-urile din repository intr-o locatie dorita folosind comanda:
		git clone https://github.com/DLC07/Licenta_Lupei_Dacian.git

	- Se lansează aplicația Thonny IDE.
	- Se deschide terminalul din Thonny IDE
	- Se navighează la scriptul Python folosind comanda cd:
	
		cd *your_path*/Scripturi_Licenta_Lupei_Dacian/Script_Raspberry_PI
				
	- Se selectează meniul Tools > Options:
	- Dupa ce se deschide fereastra de optiuni, se selectează tab-ul Interpreter
	- Se apasă pe "new virtual enviroment" pentru a crea un nou venv

- Instalarea dependențelor:

	- se instalează următoarele biblioteci folosind pip:
		pip install -r requirements_pi.txt

	- Se seletează din meniul principal python-ul aflat in venvul creat

Rularea aplicatiei:

	- Se acționează butonul F5 pentru rulare
-----------------------------------------------------------------------------

-----------------------------------------------------------------------------
Pentru a se putea realiza conexiunea wireless intre cele doua dispozitive este nevoie de urmatoarele modificari:

- ambele dispozitive trebuie să fie conectate la aceeași rețea
- se deschide script-ul app.py cu un IDE la alegere
- se modifica linia 28 prin schimbare adresei IP cu adresa ip curenta a raspberry Pi-ului (dupa "tcp/...; portul 7447 rămâne intact")
-----------------------------------------------------------------------------
