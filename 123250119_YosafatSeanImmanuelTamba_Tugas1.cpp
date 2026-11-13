#include <iostream>
using namespace std;

const int MAX_STR = 50;
bool inputClosed = false;
struct Dokter
{
    char nama[MAX_STR];
    Dokter *next;
};

struct Pasien
{
    char id[MAX_STR];
    char pemilik[MAX_STR];
    char jenis[MAX_STR];
    int durasi;
    Dokter *penanggungJawab;
    Pasien *prev;
    Pasien *next;
};

Pasien *head = nullptr;
Pasien *tail = nullptr;
Pasien *current = nullptr;
Dokter *giliran = nullptr;

int strLen(const char *s)
{
    int n = 0;
    while (s[n] != '\0')
        n++;
    return n;
}

void strCopy(char *dest, const char *src)
{
    int i = 0;
    while (src[i] != '\0')
    {
        dest[i] = src[i];
        i++;
    }
    dest[i] = '\0';
}

char toLower(char c)
{
    if (c >= 'A' && c <= 'Z')
        return c + 32;
    return c;
}

char toUpper(char c)
{
    if (c >= 'a' && c <= 'z')
        return c - 32;
    return c;
}

bool strEqualIC(const char *a, const char *b)
{
    int i = 0;
    while (a[i] != '\0' && b[i] != '\0')
    {
        if (toLower(a[i]) != toLower(b[i]))
            return false;
        i++;
    }
    return a[i] == '\0' && b[i] == '\0';
}

void normalisasi(char *s)
{
    for (int i = 0; s[i] != '\0'; i++)
    {
        s[i] = (i == 0) ? toUpper(s[i]) : toLower(s[i]);
    }
}

void readLine(char *buf, int size)
{
    cin.getline(buf, size);
    if (cin.eof())
    {
        inputClosed = true;
        if (cin.gcount() == 0)
            buf[0] = '\0';
        return;
    }
    if (cin.fail())
    {
        cin.clear();
        cin.ignore(10000, '\n');
    }
}

void printLine(int n)
{
    for (int i = 0; i < n; i++)
        cout << '=';
    cout << endl;
}

void printCentered(const char *s, int width)
{
    int len = strLen(s);
    int left = (width - len) / 2;
    int right = width - len - left;
    if (left < 0)
        left = 0;
    if (right < 0)
        right = 0;
    for (int i = 0; i < left; i++)
        cout << ' ';
    cout << s;
    for (int i = 0; i < right; i++)
        cout << ' ';
}

void tambahDokter(Dokter *&first, const char *nama)
{
    Dokter *baru = new Dokter;
    strCopy(baru->nama, nama);

    if (first == nullptr)
    {
        first = baru;
        baru->next = baru;
    }
    else
    {
        Dokter *bantu = first;
        while (bantu->next != first)
            bantu = bantu->next;
        bantu->next = baru;
        baru->next = first;
    }
}

void inisialisasiDokter()
{
    tambahDokter(giliran, "Drh. Sarah");
    tambahDokter(giliran, "Drh. Budi");
    tambahDokter(giliran, "Drh. Rina");
    tambahDokter(giliran, "Drh. Andi");
}

bool tentukanDurasi(const char *jenis, int &durasi)
{
    if (strEqualIC(jenis, "Kucing"))
    {
        durasi = 15;
        return true;
    }
    if (strEqualIC(jenis, "Anjing"))
    {
        durasi = 25;
        return true;
    }
    if (strEqualIC(jenis, "Eksotis") || strEqualIC(jenis, "Kelinci") ||
        strEqualIC(jenis, "Reptil") || strEqualIC(jenis, "Burung"))
    {
        durasi = 30;
        return true;
    }
    return false;
}

bool idSudahAda(const char *id)
{
    Pasien *bantu = head;
    while (bantu != nullptr)
    {
        if (strEqualIC(bantu->id, id))
            return true;
        bantu = bantu->next;
    }
    return false;
}

void addPet()
{
    char id[MAX_STR], pemilik[MAX_STR], jenis[MAX_STR];
    int durasi = 0;

    cout << "============ ADD PET ============" << endl;

    while (!inputClosed)
    {
        cout << "1. ID Pasien    : ";
        readLine(id, MAX_STR);
        if (inputClosed && id[0] == '\0')
            return;
        if (id[0] == '\0')
        {
            cout << "ID Pasien tidak boleh kosong!" << endl;
        }
        else if (idSudahAda(id))
        {
            cout << "ID Pasien sudah terdaftar!" << endl;
        }
        else
        {
            break;
        }
    }

    while (!inputClosed)
    {
        cout << "2. Nama Pemilik : ";
        readLine(pemilik, MAX_STR);
        if (pemilik[0] != '\0')
            break;
        cout << "Nama pemilik tidak boleh kosong!" << endl;
    }

    while (!inputClosed)
    {
        cout << "3. Jenis Hewan  : ";
        readLine(jenis, MAX_STR);
        if (tentukanDurasi(jenis, durasi))
            break;
        cout << "Jenis hewan tidak valid! (Kucing / Anjing / Eksotis)" << endl;
    }
    if (inputClosed && durasi == 0)
        return;
    normalisasi(jenis);

    cout << "4. Duration     : " << durasi << endl;

    Pasien *baru = new Pasien;
    strCopy(baru->id, id);
    strCopy(baru->pemilik, pemilik);
    strCopy(baru->jenis, jenis);
    baru->durasi = durasi;
    baru->penanggungJawab = nullptr;
    baru->prev = tail;
    baru->next = nullptr;

    if (tail == nullptr)
    {
        head = tail = baru;
    }
    else
    {
        tail->next = baru;
        tail = baru;
    }

    cout << "Pasien " << baru->id << " telah masuk ke dalam antrian" << endl;
}

void servePet()
{
    cout << "============= SERVE PET =============" << endl;

    Pasien *target = (current == nullptr) ? head : current->next;

    if (target == nullptr)
    {
        cout << "antrean kosong" << endl;
        return;
    }

    current = target;
    current->penanggungJawab = giliran;

    cout << "Pasien " << current->id << " sedang diperiksa oleh: "
         << giliran->nama << endl;

    giliran = giliran->next;
}

void checkQueue()
{
    Pasien *prevP = (current != nullptr) ? current->prev : nullptr;
    Pasien *nextP = (current != nullptr) ? current->next : head;

    const int W = 11;
    cout << "============ CHECK QUEUE ============" << endl;
    cout << "|";
    printCentered("prev", W);
    cout << "|";
    printCentered("current", W);
    cout << "|";
    printCentered("next", W);
    cout << "|" << endl;
    printLine(37);

    cout << "|";
    printCentered(prevP ? prevP->id : "tidak ada", W);
    cout << "|";
    printCentered(current ? current->id : "tidak ada", W);
    cout << "|";
    printCentered(nextP ? nextP->id : "tidak ada", W);
    cout << "|" << endl;
}

void showMenu()
{
    cout << endl;
    cout << "============ WELCOME ============" << endl;
    cout << "|          TO PETCARE!          |" << endl;
    printLine(33);
    cout << "1. Add Pet" << endl;
    cout << "2. Serve Pet" << endl;
    cout << "3. Check Queue" << endl;
    cout << "4. Exit" << endl;
    printLine(33);
    cout << "Masukkan pilihan menu: ";
}

bool kembaliKeMenu()
{
    char buf[MAX_STR];
    while (!inputClosed)
    {
        printLine(33);
        cout << "Apakah kembali ke menu? (y/n): ";
        readLine(buf, MAX_STR);
        if (buf[1] == '\0')
        {
            if (buf[0] == 'y' || buf[0] == 'Y')
                return true;
            if (buf[0] == 'n' || buf[0] == 'N')
                return false;
        }
        cout << "Masukkan hanya y atau n!" << endl;
    }
    return false;
}

void pesanKeluar()
{
    cout << "Terimakasih telah menggunakan PetCare!" << endl;
    printLine(33);
}

void hapusSemua()
{

    Pasien *p = head;
    while (p != nullptr)
    {
        Pasien *hapus = p;
        p = p->next;
        delete hapus;
    }
    head = tail = current = nullptr;

    if (giliran != nullptr)
    {
        Dokter *d = giliran->next;
        giliran->next = nullptr;
        while (d != nullptr)
        {
            Dokter *hapus = d;
            d = d->next;
            delete hapus;
        }
        giliran = nullptr;
    }
}

int main()
{

    inisialisasiDokter();

    char buf[MAX_STR];
    bool berjalan = true;

    while (berjalan && !inputClosed)
    {
        showMenu();
        readLine(buf, MAX_STR);
        if (inputClosed && buf[0] == '\0')
            break;

        char pilihan = (buf[0] != '\0' && buf[1] == '\0') ? buf[0] : '0';

        switch (pilihan)
        {
        case '1':
            addPet();
            if (!kembaliKeMenu())
            {
                pesanKeluar();
                berjalan = false;
            }
            break;
        case '2':
            servePet();
            if (!kembaliKeMenu())
            {
                pesanKeluar();
                berjalan = false;
            }
            break;
        case '3':
            checkQueue();
            if (!kembaliKeMenu())
            {
                pesanKeluar();
                berjalan = false;
            }
            break;
        case '4':
            pesanKeluar();
            berjalan = false;
            break;
        default:
            cout << "Pilihan tidak valid! Masukkan angka 1-4." << endl;
        }
    }

    hapusSemua();
    return 0;
}