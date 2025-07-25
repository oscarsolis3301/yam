$MainDBPath = "users_database"
$RecentLoginsPath = "Recent Logins"

# Ensure the main database directory exists
if (-not (Test-Path $MainDBPath)) {
    New-Item -ItemType Directory -Path $MainDBPath -Force | Out-Null
}

# Ensure the "Recent Logins" directory exists
if (-not (Test-Path $RecentLoginsPath)) {
    New-Item -ItemType Directory -Path $RecentLoginsPath -Force | Out-Null
}

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
        LockedOut           = $user.LockedOut
        PasswordExpired     = $user.PasswordExpired
        AccountStatus       = if ($user.Enabled) { "Enabled" } else { "Disabled" }
        LastChecked         = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    }
}

function Load-UserFromFile {
    param([string]$Username)

    $userFile = "$MainDBPath\$Username.txt"

    if (Test-Path $userFile) {
        try {
            $content = Get-Content $userFile -Raw
            return $content | ConvertFrom-Json
        } catch {
            Write-Host "Corrupt user file detected for $Username. Resetting file..." -ForegroundColor Red
            Remove-Item $userFile -Force
            return $null
        }
    }

    return $null
}

function Save-UserToFile {
    param([string]$Username, [hashtable]$UserInfo)

    $userFile = "$MainDBPath\$Username.txt"
    $UserInfo | ConvertTo-Json -Depth 5 | Set-Content -Path $userFile
}

function Get-UserByUsername {
    param([string]$Username)

    if (-not $Username) {
        return
    }

    Import-Module ActiveDirectory

    $adUser = Get-ADUser -Filter "(SamAccountName -eq '$Username') -or (EmployeeNumber -eq '$Username') -or (CN -eq '$Username')" -Properties * -ErrorAction SilentlyContinue

    if (-not $adUser) {
        return "{}"
    }

    $currentInfo = Write-UserBlock -user $adUser
    $currentInfo | ConvertTo-Json -Depth 5 | Write-Output
}

function Log-UserLogin {
    param([string]$Username)

    # Get the current timestamp
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")

    # Log the username and timestamp into the Recent Logins directory
    $loginFilePath = "$RecentLoginsPath\logins.txt"
    $loginRecord = "$timestamp - $Username`n"
    Add-Content -Path $loginFilePath -Value $loginRecord
}

function Load-RecentLogins {
    $loginFilePath = "$RecentLoginsPath\logins.txt"
    if (Test-Path $loginFilePath) {
        return Get-Content $loginFilePath
    }
    return @()
}

function Save-RecentLogins {
    param([array]$Logins)

    $loginFilePath = "$RecentLoginsPath\logins.txt"
    $Logins | Set-Content -Path $loginFilePath
}

# Main block
$username = $env:USERNAME  # Get the username of the logged-in user

# Log the user login
Log-UserLogin -Username $username

# Command-line Argument Support
if ($args.Count -gt 0) {
    Get-UserByUsername -Username $args[0]
    exit 0  # ✅ Exit here so nothing else prints
}

# Optional: Load and display recent logins when run manually
$recentLogins = Load-RecentLogins
Write-Host "Recent Logins:"
$recentLogins | ForEach-Object { Write-Host $_ }
