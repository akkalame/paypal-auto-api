import sys
from PyQt5 import QtWidgets
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QTableWidget
from PyQt5.QtCore import QThread, pyqtSignal, Qt
import re
from main import Invoices
import os

currency_codes = "USD, AUD, BRL, CAD, CNY, CZK, DKK, EUR, HKD, HUF, ILS, JPY, MYR, MXN, TWD, NZD, NOK, PHP, PLN, GBP, RUB, SGD, SEK, CHF, THB"
colores = {"azul":"#2196F3", "rojo":"#FF5722", "verde":"#4CAF50"}
testing = False

class SendThread(QThread):
    finished = pyqtSignal()

    def __init__(self, parent):
        super().__init__()
        self.mainApp = parent

    def run(self):
        self.send()
        self.finished.emit()

    def send(self):
        
        self.mainApp.igualar_names_address()

        print('creando invoice object')
        invoices = Invoices()
        print('obteniendo bearer token')
        invoices.get_bearer_token(self.mainApp.client_id_entry.text(), self.mainApp.secret_entry.text())
        #print(invoices.bearer)
        print('recorriendo recipients')
        for i in range(self.mainApp.listbox.count()):
            print('')
            list_item = self.mainApp.listbox.item(i)
            list_item.setForeground(QColor('#fff'))
            list_item.setBackground(QColor(colores['azul']))
            fail_response = None
            try:
                
                recipient = list_item.text()
                name_recipient = (self.mainApp.listbox_names.item(i).text().split(',') 
                    if self.mainApp.listbox_names.count() > 0 else [])
                address_recipient = (self.mainApp.listbox_address.item(i).text().split(',') 
                    if self.mainApp.listbox_address.count() > 0 else [])
                #list_item.setData(1,'azul')

                print('usando recipiente: ', recipient)
                note = self.mainApp.note_entry.text()
                terms = self.mainApp.terms_text.toPlainText()
                invoicer = self.mainApp.email_entry.text() if self.mainApp.email_entry.text() != '' else None
                cc = self.mainApp.cc_text.toPlainText().strip().split(',') if self.mainApp.cc_text.toPlainText() else []

                print(f'recorriendo items ({self.mainApp.table.rowCount()})')
                items = []
                for row in range(self.mainApp.table.rowCount()):
                    newItem = {
                            'name':self.mainApp.table.cellWidget(row, 0).text(),
                            'description':self.mainApp.table.cellWidget(row, 1).text(),
                            'qty':self.mainApp.table.cellWidget(row, 2).text(),
                            'value':self.mainApp.table.cellWidget(row, 3).text()
                    }
                    items.append(newItem)
                    
                    #print('nuevo item agregado \n',newItem)

                website = self.mainApp.website_entry.text()
                tax_id = self.mainApp.tax_id_entry.text()
                currency = self.mainApp.currency_cbox.currentText()
                phone = self.mainApp.phone_entry.text()

                # (self, recipient, items, note='', terms='', invoicer=None, cc=[], website='',
                    #tax_id='', phones='', name_recipient=[], address_recipient=None ):
                print('formateando data')       
                json_data = invoices.format_json_data(recipient=recipient, items=items,
                     note=note, terms=terms, invoicer=invoicer, cc=cc, website=website,
                    tax_id=tax_id, phone=phone, name_recipient=name_recipient, 
                    address_recipient=address_recipient, currency=currency)
                #print(json_data)

                print('creando draft')
                draft_response = invoices.create_draft_invoice(json_data)
                id_invoice = invoices.get_id_from_url(draft_response['href'])
                print('enviando invoice')
                response = invoices.send_invoice(id_invoice)
                fail_response = response
                print(response['href'])
                list_item.setBackground(QColor(colores['verde']))
                #list_item.setData(1,'verde')
            except Exception as e:
                print('falla al enviar invoice al recipiente')
                #list_item.setData(1,'rojo')
                print(fail_response)
                list_item.setBackground(QColor(colores['rojo']))
                print(e)

        print('The script is finished')

class DropableFilesQListWidget(QtWidgets.QListWidget):
    droped = pyqtSignal(list)

    def __init__(self):
        super().__init__();
        self.setAcceptDrops(True);
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)

    def dragEnterEvent(self, event):

        if event.mimeData().hasUrls():
            event.acceptProposedAction() 
        else:
             event.ignore()

    def dropEvent(self, event):

        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
            links=[]
            for url in event.mimeData().urls():
                links.append(str(url.toLocalFile()))
            self.droped.emit(links)
            
        else:
            event.ignore()

class App(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('My App')
        self.left_frame = QtWidgets.QFrame()
        self.right_frame = QtWidgets.QFrame()
        self.create_left_widgets()
        self.create_right_widgets()

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.left_frame)
        layout.addWidget(self.right_frame)
        self.setLayout(layout)

        with open('estilos.css', mode='r') as f:
            estilos = f.read()
        self.setStyleSheet(estilos)

    def create_left_widgets(self):
        self.invoicer_group = QtWidgets.QGroupBox("Invoicer")
        self.email_label = QtWidgets.QLabel("Email invoicer")
        self.email_entry = QtWidgets.QLineEdit()
        if testing:
            self.email_entry.setText('')

        self.website_label = QtWidgets.QLabel("Website")
        self.website_entry = QtWidgets.QLineEdit()
        if testing:
            self.website_entry.setText('')

        self.tax_id_label = QtWidgets.QLabel("Tax ID")
        self.tax_id_entry = QtWidgets.QLineEdit()
        if testing:
            self.tax_id_entry.setText('')

        self.phone_label = QtWidgets.QLabel("Phone (001)")
        self.phone_entry = QtWidgets.QLineEdit()
        if testing:
            self.phone_entry.setText('')

        self.client_group = QtWidgets.QGroupBox("Client ID and Secret")
        self.client_id_label = QtWidgets.QLabel("Client ID")
        self.client_id_entry = QtWidgets.QLineEdit()
        if testing:
            self.client_id_entry.setText('')

        self.secret_label = QtWidgets.QLabel("Secret")
        self.secret_entry = QtWidgets.QLineEdit()
        if testing:
            self.secret_entry.setText('')

        self.cc_label = QtWidgets.QLabel("CC")
        self.cc_text = QtWidgets.QTextEdit()
        self.note_label = QtWidgets.QLabel("Note")
        self.note_entry = QtWidgets.QLineEdit()
        if testing:
            self.note_entry.setText('nota de venta')

        self.terms_label = QtWidgets.QLabel("Terms")
        self.terms_text = QtWidgets.QTextEdit()

        # Crear el QComboBox
        self.label_currency = QtWidgets.QLabel("Currency")
        self.currency_cbox = QtWidgets.QComboBox(self)
        self.currency_cbox.setGeometry(50, 50, 200, 30)
        # Agregar opciones al QComboBox
        for currency_code in currency_codes.split(','):
            self.currency_cbox.addItem(currency_code)

        # Crear la tabla
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(4)
        self.table.setMinimumHeight(200)
        self.table.setMinimumWidth(500)
        if testing:
            self.add_product()

        # Crear botón para agregar nuevo producto
        self.add_button = QtWidgets.QPushButton("Add Item")
        self.add_button.clicked.connect(self.add_product)

        self.send_button = QtWidgets.QPushButton("Send")
        self.send_button.clicked.connect(self.start_send_thread)

        client_layout = QtWidgets.QGridLayout()
        client_layout.addWidget(self.client_id_label, 0,0)
        client_layout.addWidget(self.client_id_entry, 0,1)
        client_layout.addWidget(self.secret_label, 1,0)
        client_layout.addWidget(self.secret_entry, 1,1)
        self.client_group.setLayout(client_layout)

        # layout invoicer
        invoicer_layout = QtWidgets.QGridLayout()
        invoicer_layout.addWidget(self.email_label, 0, 0)
        invoicer_layout.addWidget(self.email_entry, 0, 1)
        invoicer_layout.addWidget(self.website_label, 1, 0)
        invoicer_layout.addWidget(self.website_entry, 1, 1)
        invoicer_layout.addWidget(self.tax_id_label, 2, 0)
        invoicer_layout.addWidget(self.tax_id_entry, 2, 1)
        invoicer_layout.addWidget(self.phone_label, 3, 0)
        invoicer_layout.addWidget(self.phone_entry, 3, 1)
        self.invoicer_group.setLayout(invoicer_layout)

        left_layout = QtWidgets.QGridLayout()
        left_layout.addWidget(self.invoicer_group, 0, 0, 1, 2)
        left_layout.addWidget(self.client_group, 1, 0, 1, 2)
        left_layout.addWidget(self.cc_label, 2, 0)
        left_layout.addWidget(self.cc_text, 2, 1)
        left_layout.addWidget(self.note_label, 3, 0)
        left_layout.addWidget(self.note_entry, 3, 1)
        left_layout.addWidget(self.terms_label, 4, 0)
        left_layout.addWidget(self.terms_text, 4, 1)
        left_layout.addWidget(self.label_currency, 5, 0)
        left_layout.addWidget(self.currency_cbox, 5, 1)
        left_layout.addWidget(self.add_button, 6,0)
        left_layout.addWidget(self.table, 6, 1)
        left_layout.addWidget(self.send_button, 7, 0, 1, 2)
        self.left_frame.setLayout(left_layout)

    def create_right_widgets(self):
        self.listbox = DropableFilesQListWidget()
        self.load_button = QtWidgets.QPushButton("Load recipients")
        self.load_button.clicked.connect(lambda:self.load_recipients(''))
        self.listbox.droped.connect(lambda r: self.load_recipients(r[0]))

        # names recipients
        self.listbox_names = DropableFilesQListWidget()
        self.load_names_button = QtWidgets.QPushButton("Load Names")
        self.load_names_button.clicked.connect(lambda:self.load_names(''))
        self.listbox_names.droped.connect(lambda r: self.load_names(r[0]))

        # address recipients
        self.listbox_address = DropableFilesQListWidget()
        self.load_address_button = QtWidgets.QPushButton("Load address")
        self.load_address_button.clicked.connect(lambda:self.load_address(''))
        self.listbox_address.droped.connect(lambda r: self.load_address(r[0]))

        right_layout = QtWidgets.QVBoxLayout()
        right_layout.addWidget(self.listbox)
        right_layout.addWidget(self.load_button)
        right_layout.addWidget(self.listbox_names)
        right_layout.addWidget(self.load_names_button)
        right_layout.addWidget(self.listbox_address)
        right_layout.addWidget(self.load_address_button)
        self.right_frame.setLayout(right_layout)

    def add_product(self):
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)

        # Agregar widgets QLineEdit para que el usuario pueda ingresar la información del producto
        name_edit = QtWidgets.QLineEdit()
        name_edit.setPlaceholderText("Name")
        if testing:
            name_edit.setText("gorra")

        description_edit = QtWidgets.QLineEdit()
        description_edit.setPlaceholderText("Description")
        if testing:
            description_edit.setText("negra")

        qty_edit = QtWidgets.QLineEdit()
        qty_edit.setPlaceholderText("Quantity")
        if testing:
            qty_edit.setText("1")

        value_edit = QtWidgets.QLineEdit()
        value_edit.setPlaceholderText("Value")
        if testing:
            value_edit.setText("20")

        self.table.setCellWidget(row_position, 0, name_edit)
        self.table.setCellWidget(row_position, 1, description_edit)
        self.table.setCellWidget(row_position, 2, qty_edit)
        self.table.setCellWidget(row_position, 3, value_edit) 

    def start_send_thread(self):
        self.left_frame.setEnabled(False)
        self.right_frame.setEnabled(False)
        self.send_thread = SendThread(self)
        self.send_thread.start()
        self.send_thread.finished.connect(self.on_send_thread_finished)
    
    def igualar_names_address(self):
        if self.listbox.count() > self.listbox_names.count() and self.listbox_names.count() > 0:
            restante = self.listbox.count() - self.listbox_names.count()
            for i in range(restante):
                self.listbox_names.addItem(self.listbox_names.item(i).text())

        if self.listbox.count() > self.listbox_address.count() and self.listbox_address.count() > 0:
            restante = self.listbox.count() - self.listbox_address.count()
            for i in range(restante):
                self.listbox_address.addItem(self.listbox_address.item(i).text())

    def load_recipients(self, path_file=''):
        try:
            if path_file == '':
                file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select File", "", "Text Files (*.txt)")
            else:
                file_path = path_file
            # Leer el contenido del archivo de texto
            with open(file_path, 'r') as file:
                content = file.readlines()

            self.listbox.clear()
            # Agregar las direcciones de correo electrónico al QListWidget
            for line in content:
                # Utilizar una expresión regular para buscar direcciones de correo electrónico en la línea
                matches = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', line)

                # Si se encontró una dirección de correo electrónico, agregarla al QListWidget
                if len(matches) > 0:
                    self.listbox.addItem(matches[0])
        except Exception as e:
            pass
        #self.igualar_names_address()

    def load_names(self, path_file=''):
        try:
            if path_file == '':
                file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select File", "", "Text Files (*.txt)")
            else:
                file_path = path_file
            # Leer el contenido del archivo de texto
            with open(file_path, 'r') as file:
                content = file.readlines()
            
            self.listbox_names.clear()
            # Agregar las direcciones de correo electrónico al QListWidget
            for line in content:
                self.listbox_names.addItem(line)
        except:
            pass
    
    def load_address(self, path_file=''):
        try:
            if path_file == '':
                file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select File", "", "Text Files (*.txt)")
            else:
                file_path = path_file

            # Leer el contenido del archivo de texto
            with open(file_path, 'r') as file:
                content = file.readlines()
            self.listbox_address.clear()
            # Agregar las direcciones de correo electrónico al QListWidget
            for line in content:
                self.listbox_address.addItem(line)
        except:
            pass
    
    # eventos
    def on_send_thread_finished(self):
        self.left_frame.setEnabled(True)
        self.right_frame.setEnabled(True)
    
    
if __name__ == '__main__':

    try:
        print('iniciando QApplication')
        app = QtWidgets.QApplication(sys.argv)
        print('instanciando app')
        window = App()
        print('mostrando app')
        window.show()
        
    except Exception as e:
        with open('error.log', 'a') as f:
            f.write(str(e))

    sys.exit(app.exec_())