# Keytab API

Kerberos 인증시 필요한 Keytab 파일을 생성하는 API

## Requirement

* HttpFS가 설치되어 있어야 합니다.
* Keytab을 생성하기 위한 사용자로 실행해야 합니다.

## PyPi 패키지 설치

```
> pip3 install flask flasgger hdfs
```

## Flask App의 윈도 서비스 등록

https://nssm.cc 사이트에서 NSSM을 다운로드(https://nssm.cc/release/nssm-2.24.zip) 한 후 압축을 해제합니다.

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

## HDFS를 위한 Proxy User 등록

Windows Server에서 `kadmin`으로 HDFS에 Keytab 파일을 업로드하려면 HDFS에 권한이 필요합니다. 이를 위해서 해당 계정을 proxy user 로 등록하여 super user 권한을 갖도록 설정하도록 합니다.

Cloudera Manager > HDFS > Configuration > Cluster-wide Advanced Configuration Snippet (Safety Valve) for core-site.xml 설정에 다음을 추가합니다.

* `hadoop.proxyuser.kadmin.hosts` : `*` (모든 호스트 허용)
* `hadoop.proxyuser.kadmin.users` : `*` (모든 사용자 허용)
* `hadoop.proxyuser.kadmin.groups` : `*` (모든 그룹 허용)

이렇게 설정하면 다음과 같이 XML로 생성합니다.

```xml
<configuration>
    <!-- Proxy User 설정 -->
    <property>
        <name>hadoop.proxyuser.kadmin.hosts</name>
        <value>*</value>
        <description>Allow the 'kadmin' user to impersonate other users from any host</description>
    </property>

    <property>
        <name>hadoop.proxyuser.kadmin.groups</name>
        <value>*</value>
        <description>Allow the 'kadmin' user to impersonate other users from any group</description>
    </property>

    <property>
        <name>hadoop.proxyuser.kadmin.users</name>
        <value>*</value>
        <description>Allow the 'kadmin' user to impersonate any other user</description>
    </property>
</configuration>
```
