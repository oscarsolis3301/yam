$MainDBPath = "computers_database.sqlite"
$CachePath  = "computers_cache.txt"

Import-Module SQLite

function Initialize-Database {
    if (-not (Test-Path $MainDBPath)) {
        New-SqliteDatabase -Database $MainDBPath
    }

    $tableExists = (Get-SqliteTable -Database $MainDBPath) -contains "Computers"
    if (-not $tableExists) {
        Invoke-SqliteQuery -Database $MainDBPath -Query @"
CREATE TABLE IF NOT EXISTS Computers (
    Name TEXT PRIMARY KEY,
    Enabled TEXT,
    LastLogonDate TEXT,
    OUGroups TEXT,
    WorkstationClass TEXT,
    Locked TEXT,
    IPv4Address TEXT,
    Online TEXT
);
"@
    }
}

function Write-ComputerBlock {
    param(
        [Microsoft.ActiveDirectory.Management.ADComputer]$computer
    )

    $ipv4 = "N/A"
    $online = $false
    $hostname = $computer.DNSHostName
    if (-not $hostname) {
        $hostname = $computer.Name
    }

    try {
        $online = Test-Connection -ComputerName $hostname -Count 1 -Quiet -ErrorAction Stop
        if ($online) {
            $resolvedIPs = [System.Net.Dns]::GetHostAddresses($hostname) |
                           Where-Object { $_.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork }
            if ($resolvedIPs.Count -gt 0) {
                $ipv4 = $resolvedIPs[0].IPAddressToString
            }
        }
    } catch {
        $online = $false
        $ipv4 = "N/A"
    }

    return @{
        Name             = $computer.Name
        Enabled          = $computer.Enabled
        LastLogonDate    = if ($computer.LastLogonDate) {
            [System.DateTime]::Parse($computer.LastLogonDate).ToString("yyyy-MM-dd HH:mm:ss")
        } else {
            "Never"
        }
        OUGroups         = $computer.CanonicalName
        WorkstationClass = $computer.ObjectClass
        Locked           = $computer.LockedOut
        IPv4Address      = $ipv4
        Online           = $online
    }
}

function Save-ComputerToDatabase {
    param (
        [hashtable]$Computer
    )

    $query = @"
INSERT OR REPLACE INTO Computers (
    Name, Enabled, LastLogonDate, OUGroups, WorkstationClass, Locked, IPv4Address, Online
) VALUES (
    @Name, @Enabled, @LastLogonDate, @OUGroups, @WorkstationClass, @Locked, @IPv4Address, @Online
);
"@

    Invoke-SqliteQuery -Database $MainDBPath -Query $query -SqlParameters @{
        Name             = $Computer.Name
        Enabled          = $Computer.Enabled
        LastLogonDate    = $Computer.LastLogonDate
        OUGroups         = $Computer.OUGroups
        WorkstationClass = $Computer.WorkstationClass
        Locked           = $Computer.Locked
        IPv4Address      = $Computer.IPv4Address
        Online           = $Computer.Online
    }
}

function Get-ComputerFromDatabase {
    param (
        [string]$ComputerName
    )

    $query = "SELECT * FROM Computers WHERE Name = @ComputerName;"
    $results = Invoke-SqliteQuery -Database $MainDBPath -Query $query -SqlParameters @{ ComputerName = $ComputerName }

    return $results
}

function Load-Cache {
    if (Test-Path $CachePath) {
        $json = Get-Content $CachePath -Raw
        if ($json -and $json.Trim() -ne '') {
            try {
                return $json | ConvertFrom-Json
            } catch {
                Write-Host "Corrupt cache detected. Resetting cache..." -ForegroundColor Red
                return @()
            }
        }
    }
    return @()
}

function Save-Cache($CacheData) {
    if ($CacheData.Count -eq 1) {
        $CacheData = @($CacheData)
    }
    $CacheData | ConvertTo-Json -Depth 5 | Set-Content -Path $CachePath
}

function Get-ComputerByName {
    param (
        [string]$ComputerName
    )

    if (-not $ComputerName) {
        return
    }

    Initialize-Database

    # Try SQLite first
    $FromDb = Get-ComputerFromDatabase -ComputerName $ComputerName
    if ($FromDb.Count -gt 0) {
        return $FromDb[0] | ConvertTo-Json -Depth 3 -Compress
    }

    # Fall back to AD
    Import-Module ActiveDirectory
    $computer = Get-ADComputer -Filter "(Name -eq '$ComputerName') -or (DNSHostName -eq '$ComputerName')" -Properties * -ErrorAction SilentlyContinue

    if (-not $computer) {
        return "{}"
    }

    $ComputerInfo = Write-ComputerBlock -computer $computer

    # Save to SQLite and cache
    Save-ComputerToDatabase -Computer $ComputerInfo

    $CacheData = Load-Cache
    $CacheData += $ComputerInfo
    Save-Cache -CacheData $CacheData

    return $ComputerInfo | ConvertTo-Json -Depth 3 -Compress
}

# If script is run with a computer name argument
if ($args.Count -gt 0) {
    Get-ComputerByName -ComputerName $args[0]
}
