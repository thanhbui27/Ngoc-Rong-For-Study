# Hướng dẫn deploy Ngọc Rồng lên Ubuntu VPS

Tài liệu này áp dụng cho repository `thanhbui27/Ngoc-Rong-For-Study`: hai ứng dụng Java 17 (`Login`, `Server`) chạy bằng systemd và một MariaDB 10.11 chạy bằng Docker Compose. Các lệnh dưới đây ghi rõ nơi thực hiện. Dùng `deploy` cho Git/Maven/Java; dùng tài khoản quản trị VPS cho Docker, systemd và tạo file hệ thống.

> **Trạng thái đã kiểm tra ngày 17/11/2026:** VPS `vps12` tại `103.116.52.124` có MariaDB với 55 bảng; `nro-login` và `nro-server` đã chạy, lần lượt nghe cổng `3105` và `14445`. Ở thời điểm kiểm tra, GitHub `main` mới có `deploy.sh`; file `.github/workflows/deploy.yml` chỉ có trong checkout local. Luôn kiểm tra lại trạng thái trước khi làm các bước liên quan.

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

Container phải hiển thị `Up` và `127.0.0.1:3306->3306/tcp`. Với **volume trống**, image sẽ import `ngocrong-clean.sql` từ `/docker-entrypoint-initdb.d`. Seed này chứa schema và dữ liệu mẫu game, không chứa tài khoản/nhân vật cũ. `ngocrong.sql` là dump riêng tư, được Git bỏ qua.

Kiểm tra DB bằng user ứng dụng mà không in mật khẩu:

```bash
docker compose exec -T db sh -c 'MYSQL_PWD="$MARIADB_PASSWORD" mariadb -N -u"$MARIADB_USER" "$MARIADB_DATABASE" -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE();"'
```

Số bảng phải lớn hơn 0; trên VPS đã kiểm tra được 55. Các biến `MARIADB_*` và script import chỉ có tác dụng khởi tạo khi thư mục dữ liệu còn trống. **Sau khi DB đã có dữ liệu, sửa `.env` không tự đổi mật khẩu trong MariaDB và không import lại SQL.** Muốn đổi mật khẩu, sao lưu DB, đổi user bằng SQL, rồi cập nhật `.env` và cả hai file cấu hình Java cho khớp. Xem [tài liệu MariaDB về biến khởi tạo](https://mariadb.com/docs/server/server-management/automated-mariadb-deployment-and-administration/docker-and-mariadb/mariadb-server-docker-official-image-environment-variables).

`compose.yaml` hiện chưa khai báo chính sách tự khởi động lại DB. Sau khi VPS reboot, kiểm tra `docker compose ps` và chạy `docker compose up -d db` nếu container chưa chạy. Nếu muốn DB tự khởi động cùng Docker, thêm `restart: unless-stopped` vào service `db` trong **Compose canonical** rồi áp dụng bằng `docker compose up -d db` sau khi đã sao lưu; [Docker giải thích chính sách này tại đây](https://docs.docker.com/reference/compose-file/services/#restart). Không dùng một Compose file/stack khác cho cùng DB.

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

### Quyền restart cho user deploy

`deploy.sh` gọi hai lệnh `sudo systemctl restart`. Tạo rule giới hạn:

```bash
sudo visudo -f /etc/sudoers.d/nro-deploy
```

Nội dung:

```text
deploy ALL=(root) NOPASSWD: /usr/bin/systemctl restart nro-login, /usr/bin/systemctl restart nro-server
```

Kiểm tra:

```bash
sudo visudo -cf /etc/sudoers.d/nro-deploy
sudo -l -U deploy
```

User `deploy` không cần `sudo` toàn quyền cho pipeline này. Nếu VPS cũ đã cấp `(ALL : ALL) ALL`, rà soát quyền đó trước khi dùng production; đừng cấp quyền ghi file systemd cho `deploy`.

## 6. Deploy tay lần đầu

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

### 7.2. Host key của VPS

Host key xác thực **VPS** khác với key đăng nhập của user `deploy`. Trên Windows sau khi đã xác minh VPS:

```powershell
ssh-keygen -F 103.116.52.124
```

Dùng **một dòng bắt đầu bằng `103.116.52.124 ssh-...`** trong `known_hosts` làm secret `VPS_KNOWN_HOSTS`. Không copy dòng chú thích `# Host ...`, không copy private key và không lấy host key từ kết nối chưa xác minh. VPS hiện dùng host key RSA trong Windows `known_hosts`; SSH runner chấp nhận miễn dòng này khớp với key thực của VPS.

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

File cần có trên **GitHub `main`** là `.github/workflows/deploy.yml`; có ở máy Windows nhưng chưa push thì trang Actions sẽ hiện “No workflows found”. Workflow hiện chạy khi push `main` hoặc chọn **Run workflow** thủ công. Nó tạo `~/.ssh/id_ed25519`, `known_hosts`, sau đó SSH vào VPS chạy `./deploy.sh`.

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

Xem diff trước khi push: checkout local hiện có merge commit khôi phục **nhiều thay đổi code**, không chỉ workflow. Push `main` sẽ kích hoạt deploy bản code mới. Không dùng `git push --force` để giải quyết nhánh rẽ; nó đã từng làm mất workflow trên remote. Sau khi chấp nhận diff và tạo đủ secrets:

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
