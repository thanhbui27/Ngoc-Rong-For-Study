# Hướng dẫn deploy Ngọc Rồng lên Ubuntu VPS

Tài liệu này áp dụng cho repository `thanhbui27/Ngoc-Rong-For-Study`: hai ứng dụng Java 17 (`Login`, `Server`) chạy bằng systemd và một MariaDB 10.11 chạy bằng Docker Compose. Các lệnh dưới đây ghi rõ nơi thực hiện. Dùng `deploy` cho Git/Maven/Java; dùng tài khoản quản trị VPS cho Docker, systemd và tạo file hệ thống.

> **Ví dụ trong tài liệu dùng VPS vps12, IP 103.116.52.124.** MariaDB và hai service Java đã được thiết lập trên VPS này. GitHub main hiện đã có workflow. Trạng thái container, service và lần chạy Actions có thể thay đổi; kiểm tra lại bằng các lệnh ở mục 6 và 8 trước khi quyết định bước tiếp.

## 0. Cách đọc nếu bạn mới bắt đầu

Tài liệu có ba nơi chạy lệnh khác nhau. Khối ghi **Trên Windows PowerShell** chạy trên máy Windows. Khối ghi **Trên VPS, bằng tài khoản quản trị** chạy trên VPS với quyền root hoặc sudo. Khối ghi **dùng user deploy** chạy trên VPS bằng user deploy. Dấu nhắc như PS C:\> hoặc deploy@vps:~$ chỉ là ví dụ về terminal; không gõ dấu nhắc đó. Chạy từng khối theo thứ tự và dừng tại lỗi đầu tiên.

| Từ thường gặp | Hiểu đơn giản |
| --- | --- |
| VPS | Máy Linux chạy game ở trên mạng; khác máy Windows của bạn. |
| Repository/repo | Thư mục source được Git quản lý. GitHub giữ bản trên mạng; VPS và Windows có hai bản sao riêng. |
| Git branch main | Nhánh code mà script và GitHub Actions lấy để deploy. |
| git add / commit / push | Chọn file muốn đưa vào lần lưu tiếp theo / lưu thành commit trên máy / gửi commit lên GitHub. |
| Docker Engine | Chương trình chạy container. Docker Compose đọc file compose.yaml để tạo đúng service DB đã khai báo. |
| Container / image / volume | Container là tiến trình DB; image là bộ cài MariaDB; volume là nơi giữ dữ liệu DB sau khi container dừng hoặc tạo lại. |
| systemd service | Cách Ubuntu chạy Java nền và tự khởi động lại khi tiến trình lỗi. |
| SSH key | Cặp khóa đăng nhập: private key chỉ giữ riêng, public key đặt trong authorized_keys trên VPS. |
| GitHub Secret | Giá trị bí mật được lưu trong Settings của repo để workflow dùng; không nằm trong code. |
| JAR | File Java được Maven build; Login.jar và Server.jar là hai chương trình cần chạy. |

Một vài ký hiệu trong lệnh: **sudo** chạy lệnh với quyền quản trị; **cd** đổi thư mục; **pwd** in thư mục đang đứng; **~** là thư mục nhà của user; **.** là thư mục hiện tại. **|** chuyển kết quả lệnh bên trái sang lệnh bên phải; **>** ghi kết quả vào file; **&&** chỉ chạy lệnh tiếp theo nếu lệnh trước thành công; **|| true** cho phép lệnh kiểm tra không tìm thấy kết quả mà không làm dừng cả khối. Các chữ sau dấu **#** trong khối Bash là chú thích. Nếu thấy tên như **CHON_THU_MUC_BACKUP** hoặc **IP_CÔNG_KHAI**, phải thay bằng giá trị của bạn.

Nếu đang tiếp tục trên VPS này, đọc lộ trình ngắn ngay bên dưới và mục 8 để kiểm tra Actions. Nếu cài một VPS mới, làm tuần tự từ mục 2; đừng chạy lại các lệnh tạo DB/user trên VPS đã có dữ liệu.

### Lộ trình ngắn cho VPS đang dùng

Bạn không cần chạy lại toàn bộ các bước cài đặt. Làm ba kiểm tra dưới đây trước:

1. **Trên VPS, tài khoản quản trị**, kiểm tra DB và Java:

~~~bash
cd /opt/apps/Ngoc-Rong-For-Study
docker compose ps
systemctl is-active nro-login nro-server
~~~

Lệnh đầu chuyển tới thư mục có compose.yaml. Lệnh thứ hai phải cho thấy DB **Up**. Lệnh thứ ba phải in **active** hai lần. Nếu một kết quả khác đi, xem mục 9 và 10 trước khi đụng vào GitHub Actions.

2. **Trên GitHub**, mở tab **Actions** của repo và xem lần chạy mới nhất của workflow **Deploy Ngoc Rong**. Dấu xanh chỉ nói workflow hoàn tất; vẫn kiểm tra hai service và thử client. Nếu Actions báo lỗi SSH, xem mục 8.3.

3. **Trên Windows PowerShell**, trước khi push lần tiếp theo:

~~~powershell
cd 'D:\Code\game nro\Folder Server'
git status --short
git diff --stat HEAD
~~~

**git status --short** cho biết file nào đang sửa; **git diff --stat HEAD** cho biết số dòng đã thay đổi, kể cả thay đổi đã đưa vào staging, mà chưa in nội dung. Hiện tài liệu này đang được sửa ở máy local; chỉ commit/push sau khi xem lại diff. Mọi lần push main có thể tự deploy, nên không dùng git add . nếu chưa kiểm tra các file đang có.

## 1. Cấu trúc và các giá trị cố định

| Thành phần | Giá trị |
| --- | --- |
| Source trên VPS | `/opt/apps/Ngoc-Rong-For-Study` |
| Git branch deploy | `main` |
| Docker Compose project | `game-nro` |
| MariaDB | `mariadb:10.11`, chỉ publish tại `127.0.0.1:3306` |
| DB / user ứng dụng | `ngocrong` / `nro` |
| Login | `nro-login.service`, cổng `3105` |
| Game Server | `nro-server.service`, cổng `14445` |
| File Login | `Login/server.ini` |
| File Game Server | `Server/resources/config/server.properties` |
| File DB | `.env` ở thư mục gốc repo |
| Script deploy | `deploy.sh` ở thư mục gốc repo |

Luồng cập nhật: push `main` → GitHub Actions SSH vào VPS bằng user `deploy` → chạy `deploy.sh` → script `git fetch`/`git merge --ff-only`, build hai module, copy JAR, restart hai service. Workflow **không** dùng `actions/checkout` vì build xảy ra trên VPS.

## 2. Chuẩn bị VPS và source

### 2.1. Kiểm tra trước khi cài

**Trên VPS, bằng tài khoản quản trị:**

```bash
cat /etc/os-release
free -h
java -version
mvn -version
git --version
docker context ls
docker info --format '{{.Name}}'
docker compose version
docker ps -a
docker volume ls
docker compose ls
ss -ltnp | grep -E ':(3306|3105|14445|8181) ' || true
```

Kiểm tra Docker context và tài nguyên thật **trước khi tạo** container/volume. Dùng lại engine/container/volume tương thích; không tạo thêm Docker engine, data directory, WSL hoặc stack `game-nro` thứ hai. Docker Desktop trên Windows là môi trường khác với Docker Engine trên VPS. Không xóa volume hay chạy `docker system prune` để “làm sạch”.

Nếu thiếu Java/Maven/Git:

```bash
sudo apt update
sudo apt install -y openjdk-17-jdk maven git
```

Nếu VPS chưa có Docker Engine, cài **một** engine theo [hướng dẫn Ubuntu chính thức của Docker](https://docs.docker.com/engine/install/ubuntu/), rồi cài [Compose plugin](https://docs.docker.com/compose/install/linux/). Bỏ qua bước cài nếu `docker info` và `docker compose version` đã hoạt động. Không thay engine đang có chỉ để phục vụ project này.

**Giải thích các lệnh kiểm tra ở trên:**

| Lệnh | Dùng để làm gì / nhìn kết quả nào |
| --- | --- |
| cat /etc/os-release | Xem phiên bản Ubuntu để chọn đúng hướng dẫn cài đặt. |
| free -h | Xem RAM còn trống; hậu tố h hiển thị đơn vị dễ đọc như MB/GB. |
| java -version, mvn -version, git --version | Kiểm tra Java 17, Maven và Git đã cài. Nếu báo command not found thì công cụ đó còn thiếu. |
| docker context ls | Xem Docker đang trỏ tới engine nào; dấu sao đánh dấu context đang dùng. |
| docker info --format ... | In tên engine thật, tránh vô tình thao tác engine ở máy khác. |
| docker compose version | Kiểm tra Compose plugin có sẵn. |
| docker ps -a | Liệt kê cả container đang chạy và đã dừng; không tạo hay xóa container. |
| docker volume ls | Liệt kê các kho dữ liệu Docker; cần xem trước khi tạo DB mới. |
| docker compose ls | Xem đã có stack Compose tên game-nro chưa. |
| ss -ltnp ... | Xem cổng nào đã có tiến trình lắng nghe; dấu \| grep lọc các cổng quan tâm. |
| sudo apt update | Tải danh sách gói phần mềm mới từ kho Ubuntu; chưa cài chương trình. |
| sudo apt install -y ... | Cài Java/Maven/Git còn thiếu; -y tự xác nhận câu hỏi của apt. |

### 2.2. Tạo user và clone

**Trên VPS, bằng tài khoản quản trị:**

```bash
id deploy || sudo adduser deploy
sudo install -d -o deploy -g deploy -m 755 /opt/apps
```

Nếu chưa có clone:

```bash
sudo -iu deploy
cd /opt/apps
git clone https://github.com/thanhbui27/Ngoc-Rong-For-Study.git
cd Ngoc-Rong-For-Study
git branch --show-current
git status --short
```

Nếu clone đã có, chỉ sửa quyền sở hữu source **trước khi tạo các file bí mật thuộc root**:

```bash
sudo chown -R deploy:deploy /opt/apps/Ngoc-Rong-For-Study
```

`sudo -iu deploy` chuyển về `/home/deploy`; sau đó luôn `cd /opt/apps/Ngoc-Rong-For-Study`. Không chạy `git add`, `git commit` hoặc Maven từ `~` hay dưới `root`, vì sẽ gây lỗi “not a git repository” hoặc tạo file build sở hữu root.

**Giải thích các lệnh tạo user/source:**

| Lệnh | Dùng để làm gì |
| --- | --- |
| id deploy | Kiểm tra user deploy đã tồn tại; phần sau \|\| chỉ tạo khi chưa có. |
| sudo adduser deploy | Tạo một tài khoản Linux riêng để chạy code, tránh chạy game bằng root. |
| sudo install -d -o deploy -g deploy -m 755 /opt/apps | Tạo thư mục /opt/apps; -d tạo thư mục, -o/-g đặt chủ sở hữu, -m đặt quyền truy cập. |
| sudo -iu deploy | Mở một shell đăng nhập của user deploy. Shell mới bắt đầu ở /home/deploy, nên phải cd vào repo. Gõ exit để quay về shell trước. |
| git clone ... | Tải source từ GitHub về VPS lần đầu. Không chạy lại nếu thư mục repo đã có. |
| git branch --show-current | In tên nhánh hiện tại, mong đợi main. |
| git status --short | Xem file nào đang bị sửa/thêm mà chưa commit; không in nội dung file. |
| chown -R deploy:deploy ... | Đổi chủ sở hữu cả thư mục source; -R áp dụng cho thư mục con. Chỉ dùng ở bước chuẩn bị, trước khi đặt file bí mật thuộc root vào repo. |

## 3. MariaDB bằng Docker Compose

### 3.1. Kiểm tra dữ liệu cũ

**Trên VPS, bằng tài khoản quản trị, trong repo:**

```bash
cd /opt/apps/Ngoc-Rong-For-Study
docker context ls
docker ps -a
docker volume ls
docker compose ls
ss -ltnp | grep ':3306' || true
```

`compose.yaml` hiện khai báo một service `db`, tên project ổn định `game-nro`, volume bền vững `game-nro_nro_db`, giới hạn RAM 512 MB/CPU 1 và log xoay vòng. Nếu đã có DB tương thích, kiểm tra database/user hiện có rồi dùng lại; không chạy thêm MariaDB chỉ vì container cũ đang dừng. Không import seed vào DB đã có dữ liệu người chơi.

**Giải thích:** các lệnh ở mục 3.1 chỉ kiểm tra. **docker ps -a** cho biết có container DB cũ dù nó đang dừng; **docker volume ls** cho biết dữ liệu DB cũ có thể còn tồn tại; **ss** cho biết cổng 3306 có bị chương trình khác dùng. Nếu thấy thứ gì đã có, tìm hiểu nó trước khi chạy lệnh tạo DB mới.

### 3.2. Tạo DB mới khi chưa có dữ liệu cũ

Chỉ làm bước này sau khi xác nhận không có DB/volume cần giữ:

```bash
cd /opt/apps/Ngoc-Rong-For-Study
test -e .env || cp .env.example .env
chown root:root .env
chmod 600 .env
nano .env
```

Đặt hai giá trị riêng, đủ mạnh: `NRO_DB_ROOT_PASSWORD` cho quản trị DB và `NRO_DB_PASSWORD` cho user game `nro`. Không để chuỗi `replace-with-...`. Không dán nội dung `.env` vào chat/log/commit.

```bash
docker compose config -q
docker compose up -d db
docker compose ps
```

Container phải hiển thị **Up** và cổng **127.0.0.1:3306**. Với volume trống, image sẽ import ngocrong-clean.sql từ docker-entrypoint-initdb.d. Seed này chứa schema và dữ liệu mẫu game, không chứa tài khoản/nhân vật cũ. File ngocrong.sql là dump gốc có dữ liệu cũ và hiện đang được Git theo dõi trong repository công khai theo lựa chọn của chủ repo; không dùng nó làm seed DB mới.

Kiểm tra DB bằng user ứng dụng mà không in mật khẩu:

```bash
docker compose exec -T db sh -c 'MYSQL_PWD="$MARIADB_PASSWORD" mariadb -N -u"$MARIADB_USER" "$MARIADB_DATABASE" -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE();"'
```

Số bảng phải lớn hơn 0; trên VPS đã kiểm tra được 55. Các biến `MARIADB_*` và script import chỉ có tác dụng khởi tạo khi thư mục dữ liệu còn trống. **Sau khi DB đã có dữ liệu, sửa `.env` không tự đổi mật khẩu trong MariaDB và không import lại SQL.** Muốn đổi mật khẩu, sao lưu DB, đổi user bằng SQL, rồi cập nhật `.env` và cả hai file cấu hình Java cho khớp. Xem [tài liệu MariaDB về biến khởi tạo](https://mariadb.com/docs/server/server-management/automated-mariadb-deployment-and-administration/docker-and-mariadb/mariadb-server-docker-official-image-environment-variables).

`compose.yaml` hiện chưa khai báo chính sách tự khởi động lại DB. Sau khi VPS reboot, kiểm tra `docker compose ps` và chạy `docker compose up -d db` nếu container chưa chạy. Nếu muốn DB tự khởi động cùng Docker, thêm `restart: unless-stopped` vào service `db` trong **Compose canonical** rồi áp dụng bằng `docker compose up -d db` sau khi đã sao lưu; [Docker giải thích chính sách này tại đây](https://docs.docker.com/reference/compose-file/services/#restart). Không dùng một Compose file/stack khác cho cùng DB.

**Giải thích lệnh tạo DB:**

| Lệnh | Dùng để làm gì / kết quả mong đợi |
| --- | --- |
| test -e .env \|\| cp .env.example .env | Nếu .env chưa tồn tại thì copy file mẫu. Nếu đã có, giữ nguyên để không mất mật khẩu cũ. |
| chown root:root .env | Để tài khoản quản trị sở hữu file chứa mật khẩu DB. |
| chmod 600 .env | Chỉ chủ sở hữu được đọc và sửa file; 600 là quyền đọc+ghi cho chủ sở hữu. |
| nano .env | Mở trình sửa text trong terminal. Ctrl+O rồi Enter để lưu, Ctrl+X để thoát. |
| docker compose config -q | Kiểm tra Compose và các biến trong .env có hợp lệ; -q không in mật khẩu ra màn hình. |
| docker compose up -d db | Tạo hoặc khởi động riêng service db. -d chạy nền và trả lại prompt. Không xóa volume cũ. |
| docker compose ps | Xem container db đã Up chưa và cổng có đúng 127.0.0.1:3306 không. |
| docker compose exec -T db ... | Chạy một lệnh bên trong container db; -T tắt terminal tương tác để câu lệnh SQL chạy gọn. |
| MYSQL_PWD=... mariadb ... SELECT COUNT(*) | Dùng user nro và password container đã nhận lúc khởi tạo để đếm bảng; lệnh chỉ in số, không in password hay dữ liệu người chơi. |

Trong câu lệnh SQL, **information_schema.tables** là danh sách bảng do MariaDB quản lý; **DATABASE()** là DB đang kết nối. Kết quả 55 nghĩa là seed đã tạo 55 bảng trên VPS hiện tại. Chỉ số bảng lớn hơn 0 chưa chứng minh client game hoạt động; phần đó kiểm tra ở mục 6.

## 4. File cấu hình ứng dụng

**Trên VPS, bằng tài khoản quản trị:**

```bash
cd /opt/apps/Ngoc-Rong-For-Study
test -e Login/server.ini || cp Login/server.ini.example Login/server.ini
test -e Server/resources/config/server.properties || cp Server/resources/config/server.properties.example Server/resources/config/server.properties
chown deploy:deploy Login/server.ini Server/resources/config/server.properties
chmod 600 Login/server.ini Server/resources/config/server.properties
nano Login/server.ini
nano Server/resources/config/server.properties
```

Các giá trị cần khớp:

| `.env` / Docker | `Login/server.ini` | `Server/resources/config/server.properties` |
| --- | --- | --- |
| `MARIADB_DATABASE=ngocrong` | `db.name=ngocrong` | `server.db.name=ngocrong` |
| `MARIADB_USER=nro` (trong Compose) | `db.user=nro` | `server.db.us=nro` |
| `NRO_DB_PASSWORD` | `db.password=<cùng giá trị>` | `server.db.pw=<cùng giá trị>` |
| DB publish tại `127.0.0.1:3306` | `db.host=127.0.0.1`, `db.port=3306` | `server.db.ip=127.0.0.1`, `server.db.port=3306` |

Ngoài DB, trong `Server/resources/config/server.properties`:

- `server.sv1=NgocRong:103.116.52.124:14445:0,0,0` (thay IP nếu đổi VPS). Giá trị này được gửi cho client; `127.0.0.1` sẽ khiến người chơi kết nối nhầm về máy của họ.
- `server.port=14445`; Login dùng `server.port=3105` trong `Login/server.ini`.
- Thay `server.key`, `server.key2`, `api.key` bằng các giá trị riêng, giữ bí mật. Nếu dùng tính năng web/account activation thì đặt `server.domain` phù hợp; `localhost` trong mẫu chỉ dùng để thử cục bộ.
- `api.port=8181` trong mẫu; kiểm tra ứng dụng có thực sự mở cổng này trước khi mở firewall.

Kiểm tra mà không in bí mật:

```bash
sudo -u deploy test -r Login/server.ini && sudo -u deploy test -r Server/resources/config/server.properties && echo 'Config readable'
if grep -q 'replace-with-' .env Login/server.ini Server/resources/config/server.properties; then echo 'ERROR: con gia tri mau'; else echo 'Khong con gia tri mau'; fi
if grep -q '^server\.sv1=.*127\.0\.0\.1' Server/resources/config/server.properties; then echo 'ERROR: server.sv1 van la localhost'; else echo 'server.sv1 da doi'; fi
```

`Login/server.ini`, `Server/resources/config/server.properties` và `.env` được `.gitignore` loại khỏi Git. Trên VPS clone mới, chúng **không tự xuất hiện** và phải tạo lại.

**Giải thích lệnh tạo/kiểm tra file cấu hình:**

| Lệnh | Dùng để làm gì |
| --- | --- |
| test -e ... \|\| cp ...example ... | Chỉ tạo file thật từ file mẫu nếu chưa có; không ghi đè cấu hình đang dùng. |
| chown deploy:deploy ... | Java chạy dưới user deploy nên user này phải đọc được hai file cấu hình. |
| chmod 600 ... | Giữ mật khẩu DB và key trong file không đọc được bởi user Linux khác. |
| nano ... | Sửa giá trị mẫu bằng giá trị thật; không dán mật khẩu vào chat. |
| sudo -u deploy test -r ... | Thử quyền đọc file với danh tính deploy; dòng Config readable xuất hiện nếu cả hai file đọc được. |
| grep -q ... | Tìm lặng lẽ, chỉ dùng kết quả đúng/sai; không in dòng có mật khẩu/key. |

Tên khóa ở hai file khác nhau: **db.password** của Login và **server.db.pw** của Server đều phải bằng **NRO_DB_PASSWORD** đã dùng khi DB khởi tạo. **NRO_DB_ROOT_PASSWORD** chỉ dành cho quản trị DB. Chuỗi **server.sv1** là địa chỉ gửi cho máy người chơi; vì thế phải là IP/tên miền công khai, còn **db.host** và **server.db.ip** vẫn là 127.0.0.1 vì Java và DB ở cùng VPS.

## 5. Hai systemd service

Tạo bằng tài khoản quản trị. Lệnh `systemctl cat --no-pager <tên>` kiểm tra service đã có; không cần tạo trùng file nếu nội dung đúng.

`/etc/systemd/system/nro-login.service`:

```ini
[Unit]
Description=Ngoc Rong Login
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/opt/apps/Ngoc-Rong-For-Study/Login
ExecStart=/usr/bin/java -Xms64m -Xmx192m -jar Login.jar
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/nro-server.service`:

```ini
[Unit]
Description=Ngoc Rong Game Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/opt/apps/Ngoc-Rong-For-Study/Server
ExecStart=/usr/bin/java -Xms256m -Xmx768m -jar Server.jar
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Tạo/sửa file bằng `sudo nano`, sau đó:

```bash
sudo systemctl daemon-reload
sudo systemctl enable nro-login nro-server
systemctl cat --no-pager nro-login nro-server
```

WorkingDirectory là bắt buộc vì Java đọc tài nguyên theo đường dẫn tương đối. Khởi động MariaDB và hoàn tất cấu hình ứng dụng **trước** khi start Java. Mức heap trên là điểm khởi đầu cho VPS 1 vCPU/2 GB; đo RAM thực tế bằng `free -h`, `ps`, `docker stats` rồi mới điều chỉnh.

**Giải thích file service và lệnh systemd:**

| Dòng/lệnh | Ý nghĩa |
| --- | --- |
| [Unit], Description | Tên mô tả service để bạn nhận ra khi xem trạng thái/log. |
| After=network-online.target, Wants=... | Đợi hệ thống mạng hoạt động; không bảo đảm MariaDB đã sẵn sàng, nên phải kiểm tra DB riêng. |
| [Service], Type=simple | systemd theo dõi trực tiếp tiến trình Java. |
| User=deploy | Java chạy với quyền deploy, không phải root. |
| WorkingDirectory | Chuyển vào thư mục Login hoặc Server trước khi chạy Java; các đường dẫn resources tương đối mới đúng. |
| ExecStart | Lệnh Java thật; -Xms là heap ban đầu, -Xmx là trần heap; -jar chỉ định JAR cần chạy. |
| Restart=on-failure, RestartSec=5 | Nếu Java thoát vì lỗi, systemd thử chạy lại sau 5 giây. |
| [Install], WantedBy=multi-user.target | Cho phép bật service tự chạy khi Ubuntu khởi động. |
| systemctl daemon-reload | Báo systemd đọc lại file .service sau khi sửa. |
| systemctl enable | Ghi cấu hình tự khởi động; bản thân lệnh này không chạy service ngay. |
| systemctl cat --no-pager | In toàn bộ file service, không mở màn hình cuộn; --no-pager giúp copy kết quả dễ hơn. |

### Quyền restart cho user deploy

`deploy.sh` gọi helper backup DB root-owned và hai lệnh `sudo systemctl restart`. Cài helper một lần bằng tài khoản quản trị:

```bash
cd /opt/apps/Ngoc-Rong-For-Study
sudo install -o root -g root -m 755 ops/nro-db-backup.sh /usr/local/sbin/nro-db-backup
sudo install -d -o root -g root -m 700 /var/backups/game-nro
```

Helper cố định trong `/usr/local/sbin` để user `deploy` không thể sửa lệnh chạy dưới quyền root. Tạo rule giới hạn:

```bash
sudo visudo -f /etc/sudoers.d/nro-deploy
```

Nội dung:

```text
deploy ALL=(root) NOPASSWD: /usr/local/sbin/nro-db-backup, /usr/bin/systemctl restart nro-login, /usr/bin/systemctl restart nro-server
```

Kiểm tra:

```bash
sudo visudo -cf /etc/sudoers.d/nro-deploy
sudo -l -U deploy
```

User `deploy` không cần `sudo` toàn quyền cho pipeline này. Nếu VPS cũ đã cấp `(ALL : ALL) ALL`, rà soát quyền đó trước khi dùng production; đừng cấp quyền ghi file systemd cho `deploy`.

**Giải thích sudoers:** file trong /etc/sudoers.d quyết định lệnh nào user deploy được chạy bằng sudo mà không cần gõ password. Rule ở trên chỉ cấp quyền restart hai service. **visudo** mở file và kiểm tra cú pháp an toàn; **visudo -cf** chỉ kiểm tra lại; **sudo -l -U deploy** liệt kê quyền thực tế của deploy. Không sửa sudoers bằng editor thường vì sai cú pháp có thể làm mất quyền quản trị.

## 6. Deploy tay lần đầu

### Cập nhật database an toàn

Deploy bình thường **không import lại** `ngocrong.sql` hay `ngocrong-clean.sql`. Hai file này là dump/seed; Compose chỉ dùng seed khi khởi tạo volume DB mới. Thay đổi cho database đang chạy phải được viết thành migration riêng trong `db/migrations/`.

Mỗi migration có version tăng dần và tên dạng `V2__ten_thay_doi.sql`. Không sửa file đã áp dụng; tạo version mới. `deploy.sh` backup DB trước, build server, rồi chạy `nro.db.MigrationRunner` trước khi thay JAR/restart service. Runner chỉ chạy migration chưa có trong `schema_migrations`, lưu SHA-256 để phát hiện ai sửa file đã chạy, và làm deploy dừng nếu migration lỗi. Có thể xem trước migration bằng cách chạy runner không có `--apply` từ thư mục repo:

```bash
java -cp Server/target/TeaMobi-1.0-RELEASE-jar-with-dependencies.jar nro.db.MigrationRunner
```

Để giữ dữ liệu người chơi, migration chỉ thay đổi dữ liệu cấu hình cần thiết; không dùng dump seed trên DB đang chạy, tránh `DROP`, `TRUNCATE`, xóa hàng loạt hay ghi đè bảng. `V1` thêm option template cho các set mới bằng `INSERT IGNORE`. `V2` cập nhật riêng cột `damage` của 10 hàng `power_limit` đầu để khớp các mốc sức đánh gốc; hai hàng cao nhất và các chỉ số khác được giữ nguyên.

Mỗi lần deploy (push `main` hoặc chạy workflow thủ công), `deploy.sh` tạo backup DB trước khi fetch code mới và trước khi chạy migration. Nếu backup lỗi, deploy dừng lại. Nếu migration có `ALTER TABLE`/DDL, kiểm thử trên bản DB staging/backup trước: MariaDB có các DDL tự commit, nên rollback transaction không thể hoàn tác một phần cấu trúc đã đổi. Sau deploy, kiểm tra log hai service và giữ backup cho tới khi xác nhận game chạy đúng.

**Trên VPS, dùng user `deploy`:**

```bash
sudo -iu deploy
cd /opt/apps/Ngoc-Rong-For-Study
pwd
git status --short
bash -n deploy.sh
ls -l deploy.sh
./deploy.sh
```

`pwd` phải là `/opt/apps/Ngoc-Rong-For-Study`; `deploy.sh` phải có quyền thực thi (`git ls-files --stage deploy.sh` báo mode `100755`). Build đầu có thể tải nhiều dependency Maven. Script hiện dùng `mvn clean package -DskipTests`, tức là build nhưng **không chạy test**. Script chỉ restart sau khi cả hai module build xong và tìm đúng một `*-jar-with-dependencies.jar` cho mỗi module.

Kiểm tra sau khi script kết thúc:

```bash
systemctl is-active nro-login nro-server
systemctl show nro-login nro-server -p Id -p MainPID -p ActiveState --no-pager
ps -eo pid,etime,args | grep -E '[j]ava .*-(jar|cp).*(Login|Server)\.jar' || true
ss -ltn | grep -E ':(3105|14445) ' || true
```

Từ tài khoản quản trị, xem log nếu có lỗi:

```bash
sudo journalctl -u nro-login -n 100 --no-pager
sudo journalctl -u nro-server -n 100 --no-pager
```

Cả hai service phải `active`; tiến trình Java phải chạy `Login.jar`/`Server.jar`; cổng `3105`/`14445` phải lắng nghe. Sau đó thử kết nối bằng client game. `systemctl restart` trả thành công không thay thế bước kiểm tra service/port vài giây sau.

Script hiện copy đè JAR và chưa có rollback/health check tự động. Trước thay đổi lớn, sao lưu JAR và DB; nếu cần deploy không gián đoạn hoặc rollback tự động thì phải cải tiến script riêng.

**Giải thích deploy tay và cách đọc kết quả:**

| Lệnh | Dùng để làm gì |
| --- | --- |
| bash -n deploy.sh | Chỉ kiểm tra cú pháp Bash; không build, không restart. |
| ls -l deploy.sh | Xem file có quyền thực thi hay chưa; chuỗi quyền cần có chữ x. |
| ./deploy.sh | Chạy script nằm ở thư mục hiện tại; dấu ./ là “file ở đây”. |
| git fetch / git merge --ff-only bên trong script | Tải commit mới rồi chỉ cập nhật nếu lịch sử nối thẳng; nếu nhánh đã rẽ, script dừng thay vì âm thầm ghi đè. |
| mvn clean package -DskipTests | Xóa kết quả build cũ, biên dịch và đóng gói JAR; -DskipTests bỏ qua chạy test. |
| systemctl is-active | In active/inactive cho từng service. Cả hai phải active. |
| systemctl show ... MainPID | In PID (mã số tiến trình) Java mà systemd đang theo dõi. PID bằng 0 nghĩa là không có tiến trình chính. |
| ps -eo ... | Liệt kê tiến trình để xác nhận lệnh Java đang chạy Login.jar và Server.jar. |
| ss -ltn | Xem cổng TCP đang lắng nghe; 3105 và 14445 phải xuất hiện. |
| journalctl -u ... -n 100 --no-pager | In 100 dòng log gần nhất của service để tìm lỗi; -u chọn service, -n chọn số dòng. |

Nếu terminal im lặng trong lúc Maven tải thư viện lần đầu, đợi build kết thúc. Nếu thấy **BUILD FAILURE**, gửi đoạn lỗi gần cuối log, không gửi file cấu hình có mật khẩu. Dòng **Deploy complete** chỉ nói script đi tới cuối; vẫn cần kiểm tra service và thử đăng nhập game.

## 7. SSH cho GitHub Actions

### 7.1. Key đăng nhập

**Trên Windows PowerShell:** dùng lại key hiện có nếu đã đăng nhập VPS được; không tạo key mới mỗi lần deploy.

```powershell
Test-Path "$HOME\.ssh\nro_deploy"
Test-Path "$HOME\.ssh\nro_deploy.pub"
```

Nếu chưa có key:

```powershell
ssh-keygen -t ed25519 -f "$HOME\.ssh\nro_deploy" -C "nro-github-actions"
Get-Content "$HOME\.ssh\nro_deploy.pub"
```

Dòng `ssh-ed25519 ...` từ file `.pub` phải nằm trong `/home/deploy/.ssh/authorized_keys` trên VPS. Thêm bằng tài khoản quản trị, không ghi đè các key hợp lệ đang có:

```bash
sudo install -d -o deploy -g deploy -m 700 /home/deploy/.ssh
sudo nano /home/deploy/.ssh/authorized_keys
sudo chown deploy:deploy /home/deploy/.ssh/authorized_keys
sudo chmod 600 /home/deploy/.ssh/authorized_keys
```

Kiểm tra từ Windows:

```powershell
ssh -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -i "$HOME\.ssh\nro_deploy" deploy@103.116.52.124 'id -un'
```

Kết quả phải là `deploy`. Nếu host key chưa được tin cậy, đối chiếu fingerprint của VPS qua kênh đáng tin cậy rồi mới chấp nhận; không dùng `StrictHostKeyChecking=no`.

**Giải thích các lệnh SSH:**

| Lệnh | Dùng để làm gì |
| --- | --- |
| Test-Path trên Windows | Chỉ trả về True/False để biết key đã tồn tại, không in key. |
| ssh-keygen -t ed25519 -f ... -C ... | Tạo một cặp khóa mới nếu chưa có: file không có .pub là private key; file .pub là public key; -C là nhãn để nhận ra key. |
| Get-Content ...pub | In public key để thêm vào authorized_keys; chỉ public key được phép chia sẻ. |
| install -d ... /home/deploy/.ssh | Tạo thư mục SSH cho deploy với chủ sở hữu và quyền 700. |
| nano authorized_keys | Thêm một dòng public key vào danh sách các key được phép đăng nhập. |
| chown/chmod authorized_keys | Đặt chủ sở hữu deploy và quyền 600; SSH có thể từ chối file có quyền quá rộng. |
| ssh -i ... deploy@IP | Thử đăng nhập bằng private key đã chọn. BatchMode=yes không hỏi mật khẩu; IdentitiesOnly=yes tránh dùng key khác; StrictHostKeyChecking=yes yêu cầu host key VPS đã được xác minh. |

Private key giống chìa khóa nhà: chỉ giữ trên Windows và trong GitHub Secret, không dán vào code, chat hoặc ảnh. Public key giống ổ khóa: đặt trong authorized_keys trên VPS. Nếu đã có cặp key hoạt động, dùng lại cặp đó; tạo cặp mới mà chưa đổi authorized_keys/secret sẽ gây lỗi SSH.

### 7.2. Host key của VPS

Host key xác thực **VPS** khác với key đăng nhập của user `deploy`. Trên Windows sau khi đã xác minh VPS:

```powershell
ssh-keygen -F 103.116.52.124
```

Dùng **một dòng bắt đầu bằng `103.116.52.124 ssh-...`** trong `known_hosts` làm secret `VPS_KNOWN_HOSTS`. Không copy dòng chú thích `# Host ...`, không copy private key và không lấy host key từ kết nối chưa xác minh. VPS hiện dùng host key RSA trong Windows `known_hosts`; SSH runner chấp nhận miễn dòng này khớp với key thực của VPS.

**Giải thích host key:** ssh-keygen -F IP tìm dòng VPS trong known_hosts trên Windows. Dòng này xác nhận đúng máy chủ mà GitHub runner sắp kết nối; nó **không** cấp quyền đăng nhập. Nếu host key không khớp, dừng lại để xác minh VPS, không tắt kiểm tra an toàn.

## 8. GitHub Actions tự deploy

### 8.1. Tạo 4 Repository Secrets

Vào repository trên GitHub → **Settings → Secrets and variables → Actions → Repository secrets**. Tạo:

| Secret | Giá trị |
| --- | --- |
| `VPS_HOST` | IP VPS: `103.116.52.124` |
| `VPS_USER` | `deploy` |
| `VPS_SSH_KEY` | **Toàn bộ private key nhiều dòng** từ Windows `~/.ssh/nro_deploy`, không phải `.pub` |
| `VPS_KNOWN_HOSTS` | Dòng host key đã xác minh ở mục 7.2 |

Để copy private key trên Windows mà không in ra terminal:

```powershell
Set-Clipboard -Value (Get-Content -LiteralPath "$HOME\.ssh\nro_deploy" -Raw)
```

Paste vào form GitHub, lưu, rồi xóa clipboard:

```powershell
Set-Clipboard -Value ""
```

GitHub không hiển thị lại giá trị secret đã lưu. Nếu `VPS_SSH_KEY` sai, cập nhật từ **file private key thật**, không gõ tay, không dùng chuỗi `xxxx`, không thêm dấu `\` vào `-----BEGIN/END OPENSSH PRIVATE KEY-----`. Không đưa key/token vào chat, screenshot hoặc Git. Thu hồi ngay mọi token từng bị lộ trong quá trình thiết lập. Xem [hướng dẫn GitHub về repository secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets).

### 8.2. Đưa workflow lên `main`

File workflow phải có trên **GitHub main**, không chỉ trên máy Windows. Hiện file này đã có ở main; với VPS khác hoặc khi setup lại, kiểm tra trên GitHub trước. Workflow chạy khi push main hoặc chọn Run workflow thủ công. Nó tạo file SSH key và known_hosts trên runner, sau đó SSH vào VPS chạy deploy.sh.

**Trên Windows, trong repo local:**

```powershell
cd 'D:\Code\game nro\Folder Server'
git status --short
git fetch origin main
git log --graph --oneline --decorate --all -n 12
git diff --stat origin/main..main
git ls-tree --name-only main .github/workflows/deploy.yml
git ls-tree --name-only origin/main .github/workflows/deploy.yml
```

Lệnh kiểm tra trên chỉ xem các commit đã có; file vừa sửa vẫn cần được chọn và lưu thành commit. Ví dụ, nếu bạn vừa sửa hai file tài liệu, chạy từng lệnh sau trên Windows rồi xem nội dung diff trước khi commit:

```powershell
git add -- DEPLOY.md README.md
git diff --cached --stat
git diff --cached -- DEPLOY.md README.md
git commit -m "Document VPS deployment"
git fetch origin main
git diff --stat origin/main..main
```

`git add` chỉ chọn đúng hai file trong ví dụ; `git diff --cached` cho bạn xem chính xác nội dung sắp được commit. Nếu bạn sửa `deploy.sh` hoặc workflow, thay danh sách file ở lệnh `git add` bằng đúng file cần đưa lên; dùng `git add --chmod=+x -- deploy.sh` khi cần giữ quyền chạy của script trên Linux. Nếu không có thay đổi, `git commit` sẽ báo không có gì để commit và bạn không cần push.

Xem diff trước **mỗi** lần push vì commit có thể chứa cả code, dữ liệu và workflow. Push main có thể kích hoạt deploy ngay. Không dùng `git add .` khi chưa rà soát các file, và không dùng `git push --force` để xử lý nhánh rẽ. Sau khi chấp nhận diff và tạo đủ secrets, mới chạy:

```powershell
git push origin main
```

Nếu push qua HTTPS bằng fine-grained PAT, token phải có quyền với đúng repo; khi push file trong `.github/workflows`, GitHub có thể yêu cầu cả **Contents: Read and write** và **Workflows: Read and write**. Nhập PAT ở ô password, không dùng mật khẩu tài khoản và không gắn token vào remote URL. Xem [GitHub permissions cho workflow files](https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens).

Vào **Actions → Deploy Ngoc Rong** để xem kết quả. Sau run thành công, trên VPS kiểm tra `git rev-parse HEAD`, `systemctl is-active`, log và kết nối client. Một run `workflow_dispatch` hiện vẫn deploy **`main` mới nhất**, vì `deploy.sh` tự fetch `origin/main`; nó không pin bản build vào SHA của run cũ.

### 8.3. Nếu SSH Action báo `Permission denied (publickey,password)`

1. Xác nhận `VPS_USER=deploy`, `VPS_HOST` là IP đúng.
2. Từ Windows chạy lệnh SSH ở mục 7.1 với **cùng** file `nro_deploy`.
3. Nếu Windows vào được nhưng Actions không vào được, cập nhật lại `VPS_SSH_KEY` từ file private key đó. `VPS_KNOWN_HOSTS` sai thường báo `Host key verification failed`, là lỗi khác.
4. Rerun workflow sau khi sửa secret. Không tắt xác minh host key.

**Giải thích các bước GitHub Actions:**

| Lệnh/thao tác | Dùng để làm gì |
| --- | --- |
| Set-Clipboard -Value (Get-Content ... -Raw) | Đọc nguyên file private key nhiều dòng và copy vào clipboard, không in ra terminal. Sau khi lưu secret thì xóa clipboard. |
| VPS_HOST / VPS_USER | Chỉ rõ VPS nào và user Linux nào workflow dùng để SSH. |
| VPS_SSH_KEY | Private key để GitHub runner chứng minh nó được phép đăng nhập user deploy. |
| VPS_KNOWN_HOSTS | Public host key để runner biết nó đang nói chuyện với đúng VPS. |
| git fetch origin main | Cập nhật thông tin nhánh main trên GitHub mà chưa sửa file local. |
| git log --graph ... | Vẽ lịch sử commit để nhìn thấy nhánh có bị rẽ hay không. |
| git diff --stat origin/main..main | Liệt kê số file/dòng sẽ khác khi push local lên GitHub; đây là bước xem trước, không sửa file. |
| git ls-tree --name-only ... | Kiểm tra file workflow có trong commit local/remote hay chưa. |
| git add -- ... | Chọn những file cụ thể cho commit tiếp theo; các file khác không tự được thêm. |
| git diff --cached | Xem phần đã chọn bằng git add trước khi commit. |
| git commit -m "..." | Lưu các thay đổi đã chọn thành một commit trong repo local. |
| git push origin main | Đưa commit local lên GitHub. Vì workflow chạy khi main thay đổi, push cũng có thể khởi động deploy ngay. |

Trong file workflow, **runs-on: ubuntu-latest** chọn máy chạy tạm của GitHub, **env** đưa secret vào bước chạy, **known_hosts** xác minh VPS, còn lệnh **ssh** yêu cầu VPS chạy deploy.sh. Secret sai thường làm job đỏ dù deploy tay trên VPS vẫn chạy. Trang Actions hiển thị lịch sử; một run cũ không chứng minh workflow còn tồn tại ở main hiện tại.

## 9. Vận hành, sao lưu và rollback

### 9.1. Lệnh thường dùng

**Trên VPS:**

```bash
cd /opt/apps/Ngoc-Rong-For-Study
docker compose ps
sudo systemctl status nro-login nro-server --no-pager
sudo journalctl -u nro-login -n 100 --no-pager
sudo journalctl -u nro-server -n 100 --no-pager
ss -ltn | grep -E ':(3105|14445|3306) ' || true
free -h
```

Sau reboot: kiểm tra Docker và DB trước, rồi hai service Java. Cổng `14445/tcp` cần mở cho client và SSH cần mở cho quản trị. `3306` chỉ bind loopback; không mở DB công khai. Login hiện bind `*:3105`, vì vậy phải chặn truy cập ngoài VPS tới cổng này bằng firewall của VPS/nhà cung cấp. Chỉ mở `8181` nếu API thực sự cần công khai và đã bảo vệ bằng xác thực. Kiểm tra quy tắc firewall của nhà cung cấp trước khi bật UFW để không tự khóa SSH; lưu ý [Docker có tương tác riêng với firewall/UFW](https://docs.docker.com/engine/install/ubuntu/#firewall-limitations).

### 9.2. Backup DB

**Trên VPS, bằng tài khoản quản trị:**

```bash
cd /opt/apps/Ngoc-Rong-For-Study
install -d -m 700 /var/backups/game-nro
backup_file="/var/backups/game-nro/ngocrong-$(date +%Y%m%d-%H%M%S).sql"
docker compose exec -T db sh -c 'MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb-dump -uroot --single-transaction "$MARIADB_DATABASE"' > "$backup_file"
chmod 600 "$backup_file"
test -s "$backup_file" && echo 'Backup file created'
```

Giữ bản sao backup ở vị trí khác VPS theo chính sách của bạn. Kiểm thử restore trên DB **cô lập**, không import thử vào volume đang dùng. Không dùng `docker compose down -v`, `docker volume rm`, `prune` hoặc xóa dữ liệu MariaDB để xử lý lỗi build/deploy.

### 9.3. Backup JAR và rollback

Trước deploy lớn, dưới user `deploy`:

```bash
cd /opt/apps/Ngoc-Rong-For-Study
backup_dir="/opt/apps/nro-jar-backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$backup_dir"
chmod 700 "$backup_dir"
cp Login/Login.jar "$backup_dir/Login.jar"
cp Server/Server.jar "$backup_dir/Server.jar"
printf 'JAR backup: %s\n' "$backup_dir"
```

Để rollback JAR, dùng user `deploy`, thay `CHON_THU_MUC_BACKUP` bằng tên thư mục in ra lúc backup:

```bash
cd /opt/apps/Ngoc-Rong-For-Study
backup_dir=/opt/apps/nro-jar-backups/CHON_THU_MUC_BACKUP
ls -l "$backup_dir/Login.jar" "$backup_dir/Server.jar"
cp -- "$backup_dir/Login.jar" Login/.Login.jar.rollback
cp -- "$backup_dir/Server.jar" Server/.Server.jar.rollback
mv -f -- Login/.Login.jar.rollback Login/Login.jar
mv -f -- Server/.Server.jar.rollback Server/Server.jar
sudo /usr/bin/systemctl restart nro-login
sudo /usr/bin/systemctl restart nro-server
sleep 5
systemctl is-active nro-login nro-server
```

Kiểm tra log/port sau đó. Nếu bản mới đổi schema DB hoặc tài nguyên theo code, rollback JAR đơn lẻ có thể không đủ; dùng commit/release và backup DB phù hợp. Không `git reset --hard` hoặc force-push trên VPS khi chưa xác định rõ các thay đổi cần giữ.

### 9.4. Tài khoản cũ

Nếu đã import dump cũ, hệ thống chuyển mật khẩu dạng cũ sang PBKDF2 khi đăng nhập. Để chuyển toàn bộ tài khoản chưa đăng nhập: dừng Game Server/Login, backup DB, rồi trong thư mục `Login` chạy:

```bash
java -cp Login.jar security.PasswordMigration
java -cp Login.jar security.PasswordMigration --apply
```

Lệnh đầu chỉ thống kê; lệnh thứ hai cập nhật. Không chạy `--apply` khi chưa backup DB.

**Giải thích các lệnh vận hành/backup:**

| Lệnh | Dùng để làm gì |
| --- | --- |
| docker compose ps | Xem container MariaDB hiện Up hay Exited. |
| systemctl status, journalctl | Xem trạng thái và lỗi của hai ứng dụng Java. |
| free -h | Xem VPS có còn RAM hay không. |
| install -d -m 700 /var/backups/game-nro | Tạo thư mục backup chỉ chủ sở hữu đọc được. |
| backup_file=...$(date ...) | Tạo tên file có thời gian để không ghi đè bản backup trước. |
| mariadb-dump ... > "$backup_file" | Xuất dữ liệu DB thành file SQL; dấu > ghi kết quả vào file, nên phải kiểm tra đúng tên file và quyền thư mục trước. |
| chmod 600, test -s | Giới hạn người đọc file backup; test -s kiểm tra file không rỗng. |
| cp JAR vào backup_dir | Giữ bản JAR đang chạy trước khi cập nhật. |
| mv file .rollback thành JAR | Đổi tên file tạm thành JAR chính trong cùng thư mục rồi restart service. |
| PasswordMigration không có --apply | Chỉ đếm tài khoản mật khẩu cũ, chưa sửa DB. |
| PasswordMigration --apply | Thực sự cập nhật mật khẩu cũ; chỉ chạy sau khi backup DB và dừng game. |

Backup là bản sao để khôi phục khi lỗi; nó không làm DB tự quay lại phiên bản cũ. Muốn restore DB phải thực hiện có kế hoạch trên đúng database, tránh ghi đè dữ liệu người chơi hiện tại.

## 10. Chẩn đoán nhanh

| Dấu hiệu | Kiểm tra và xử lý |
| --- | --- |
| `git: not a git repository` | Sau `sudo -iu deploy`, chạy `cd /opt/apps/Ngoc-Rong-For-Study` rồi `pwd`. |
| `git push` trả 403 | PAT/credential không có quyền đúng repo; cần `Contents: Read and write`; push workflow có thể cần thêm `Workflows: Read and write`. Không dùng password GitHub. |
| `git pull --ff-only` báo divergent | Kiểm tra `git log --graph --all` và diff; không force-push/reset trước khi giữ lịch sử cần thiết. |
| Actions báo “No workflows found” | `.github/workflows/deploy.yml` chưa có trên GitHub `main`; file local không đủ. |
| SSH Actions `Permission denied (publickey,password)` | Kiểm tra user `deploy`, private key secret nguyên vẹn, authorized_keys và quyền `.ssh`. |
| `Host key verification failed` | Kiểm tra `VPS_KNOWN_HOSTS` chứa host key VPS đúng IP/cổng; không tắt xác minh. |
| `deploy.sh: Permission denied` | `git ls-files --stage deploy.sh` cần mode `100755`; kiểm tra line ending LF. |
| Maven build lỗi | Đọc dòng `BUILD FAILURE`; `cd Login` hoặc `cd Server` và chạy `mvn clean package -DskipTests`. |
| Không tìm thấy JAR | Kiểm tra `Login/target/*-jar-with-dependencies.jar` và `Server/target/*-jar-with-dependencies.jar`; script yêu cầu mỗi module đúng một file. |
| DB login lỗi | Kiểm tra container, số bảng, `db.password` và `server.db.pw` khớp DB; đổi `.env` sau khởi tạo không đổi mật khẩu thật. |
| Service `inactive` hoặc client không vào | `journalctl`, `ss -ltn`, firewall `14445`, `server.sv1` public IP, RAM và DB. |

## 11. Checklist hoàn tất

- [ ] Có đúng một Docker engine/Compose project `game-nro` dùng cho DB trên VPS; dữ liệu nằm trong volume đã xác nhận.
- [ ] MariaDB chạy, có bảng, bind `127.0.0.1:3306`; có backup DB.
- [ ] `.env`, `Login/server.ini`, `Server/resources/config/server.properties` có quyền phù hợp, không chứa placeholder; mật khẩu DB nhất quán.
- [ ] `server.sv1` trỏ IP/tên miền công khai; chỉ mở firewall các cổng cần thiết.
- [ ] Hai unit systemd đúng `WorkingDirectory`, user `deploy`, đã enable.
- [ ] Deploy tay chạy thành công; cả hai JAR, service, cổng và client được kiểm tra.
- [ ] SSH key đăng nhập từ Windows hoạt động; host key VPS đã xác minh; bốn GitHub Secrets đã lưu.
- [ ] Workflow tồn tại trên **GitHub `main`** và run mới thành công; SHA trên VPS đúng phiên bản mong muốn.
- [ ] Các PAT từng lộ đã thu hồi; không có secret trong Git hoặc log.
- [ ] Có bản sao JAR/DB và quy trình rollback đã được diễn tập trên dữ liệu cô lập.

### Deploy khi DB đã backup và áp dụng đủ migration (không gọi Docker)

Trong Actions → **Deploy Ngoc Rong** → **Run workflow**, bật
`skip_database_backup` chỉ khi DB đã được backup và đã áp dụng đủ SQL của commit.
Script chạy migration dry-run sau khi build và dừng nếu còn migration pending;
chế độ này không chạy chương trình backup dùng Docker và không ghi migration.
SSH trực tiếp tương đương: `./deploy.sh --skip-database-backup`.
Các lần push tự deploy vẫn backup và chạy migration như trước.
