Import-Module SQLite

$SQLiteDBPath = "./db/users_cache.db"

# Ensure the SQLite module is available
Import-Module SQLite -ErrorAction SilentlyContinue
if (-not (Get-Command Invoke-SqliteQuery -ErrorAction SilentlyContinue)) {
    Write-Error "SQLite module is not available. Please install it with: Install-Module SQLite"
    exit
}

# Ensure DB file exists and table is created
function Initialize-Database {
    if (-not (Test-Path $SQLiteDBPath)) {
        New-Item -ItemType File -Path $SQLiteDBPath -Force | Out-Null
    }

    $createTableQuery = @"
CREATE TABLE IF NOT EXISTS Users (
    FullName TEXT,
    Username TEXT PRIMARY KEY,
    Email TEXT,
    DisplayName TEXT,
    PasswordLastReset TEXT,
    ClockID TEXT,
    Title TEXT,
    LockedOut TEXT,
    PasswordExpired TEXT,
    AccountStatus TEXT
);
"@
    Invoke-SqliteQuery -DataSource $SQLiteDBPath -Query $createTableQuery
}

# Escape SQL input to prevent SQL injection
function Escape-SQL {
    param ([string]$input)
    return $input -replace "'", "''"
}

# Build user data from AD user object
function Write-UserBlock {
    param(
        [Microsoft.ActiveDirectory.Management.ADUser]$user
    )

    $passwordLastReset = if ($user.PasswordLastSet) {
        try {
            [System.DateTime]::Parse($user.PasswordLastSet).ToString("yyyy-MM-dd HH:mm:ss")
        } catch {
            "Invalid Date"
        }
    } else {
        "Never Set"
    }

    return @{
        FullName            = $user.CN
        Username            = $user.SamAccountName
        Email               = $user.EmailAddress
        DisplayName         = $user.DisplayName
        PasswordLastReset   = $passwordLastReset
        ClockID             = $user.EmployeeNumber
        Title               = $user.Description
        LockedOut           = $user.LockedOut.ToString()
        PasswordExpired     = $user.PasswordExpired.ToString()
        AccountStatus       = if ($user.Enabled) { "Enabled" } else { "Disabled" }
    }
}

# Load user data from the SQLite DB
function Load-UserFromDB {
    param([string]$Username)

    $escaped = Escape-SQL $Username
    $query = @"
SELECT * FROM Users
WHERE Username = '$escaped'
   OR ClockID = '$escaped'
   OR FullName = '$escaped';
"@
    return Invoke-SqliteQuery -DataSource $SQLiteDBPath -Query $query
}

# Save user data to the SQLite DB
function Save-UserToDB {
    param([hashtable]$UserInfo)

    # Escape all fields to prevent SQL injection
    foreach ($key in $UserInfo.Keys) {
        $UserInfo[$key] = Escape-SQL ($UserInfo[$key] -as [string])
    }

    $query = @"
INSERT OR REPLACE INTO Users (
    FullName, Username, Email, DisplayName, PasswordLastReset,
    ClockID, Title, LockedOut, PasswordExpired, AccountStatus
) VALUES (
    '$($UserInfo.FullName)', '$($UserInfo.Username)', '$($UserInfo.Email)', '$($UserInfo.DisplayName)', '$($UserInfo.PasswordLastReset)',
    '$($UserInfo.ClockID)', '$($UserInfo.Title)', '$($UserInfo.LockedOut)', '$($UserInfo.PasswordExpired)', '$($UserInfo.AccountStatus)'
);
"@
    Invoke-SqliteQuery -DataSource $SQLiteDBPath -Query $query
}

# Get user by Username and return in JSON format
function Get-UserByUsername {
    param([string]$Username)

    if (-not $Username) {
        Write-Output "{}"
        return
    }

    Initialize-Database

    # Try loading user from DB first
    $CachedUser = Load-UserFromDB -Username $Username

    if ($CachedUser -and $CachedUser.Count -gt 0) {
        Write-Output ($CachedUser | ConvertTo-Json -Depth 3 -Compress)
        return
    }

    # If not found in DB, search AD
    Import-Module ActiveDirectory

    $user = Get-ADUser -Filter "(SamAccountName -eq '$Username') -or (EmployeeNumber -eq '$Username') -or (CN -eq '$Username')" -Properties * -ErrorAction SilentlyContinue

    if (-not $user) {
        Write-Output "{}"
        return
    }

    $UserInfo = Write-UserBlock -user $user
    Save-UserToDB -UserInfo $UserInfo

    Write-Output ($UserInfo | ConvertTo-Json -Depth 3 -Compress)
}

# Command-line Argument Support
if ($args.Count -gt 0) {
    Get-UserByUsername -Username $args[0]
}
