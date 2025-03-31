# Keytab API

Kerberos 인증시 필요한 Keytab 파일을 생성하는 API

## Flask App의 윈도 서비스 등록

https://nssm.cc 사이트에서 NSSM을 다운로드(https://nssm.cc/release/nssm-2.24.zip)한 후 `C:\Windows\System32`에 복사합니다.

관리자 모드로 PowerShell을 실행하고 다음의 커맨드를 실행합니다.

```
> nssm.exe install KeytabAPIService
```

서비스 설정창이 나타나면 다음과 같이 입력합니다. 

* Path : `C:\Python\python.exe`
* Start directory : `C:\apps\keytab-api\`
* Arguments : `C:\apps\keytab-api\server.py --config C:\apps\keytab-api\config.yaml`

특정 사용자로 실행하려면 Log on 탭에서 다음을 입력합니다.

* Log on as : `This account` 체크하고 사용자명 입력 (예; `kadmin`)
* Password : @!23qwe
* Confirm : @!23qwe

이제 서비스를 등록하기 위해서 Install service 버튼을 클릭합니다.

## Keytab 생성 사용자 유형

이 서비스를 등록하려면 다음과 같이 Keytab을 생성한 권한을 가진 사용자로 등록해야 합니다.

* Domain Administrator - Active Directory에서 Kerberos 관련 작업을 수행할 수 있는 권한
* Enterprise Administrator - AD 도메인에 속한 모든 도메인에 대해 관리 작업을 수행
* Custom Delegated Administrators - Kerberos 관련 권한을 명시적으로 할당한 사용자
* `krbtgt` 계정 - Kerberos 티켓을 발급하는 데 사용되는 특별한 계정

## 서비스 시작 및 부팅시 실행 설정

서비스를 시작하려면 다음과 같이 커맨드를 실행합니다.

```
> net start KeytabAPIService
```

서비스를 부팅시 자동으로 실행하도록 하려면 `service.msc`에서 "서비스 속성 > 시작 유형 > 자동" 으로 변경하거나 NSSM 실행시 "Details 탭 > Startup type > Automatic"을 설정하십시오.

