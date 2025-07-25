$MainDBPath = "users_database"

# Ensure the main database directory exists
if (-not (Test-Path $MainDBPath)) {
    New-Item -ItemType Directory -Path $MainDBPath -Force | Out-Null
}

function Write-UserBlock {
    param(
        [Microsoft.ActiveDirectory.Management.ADUser]$user
    )

    # Format password last reset date
    $passwordLastReset = if ($user.PasswordLastSet) {
        try {
            [System.DateTime]::Parse($user.PasswordLastSet).ToString("yyyy-MM-dd HH:mm:ss")
        } catch {
            "Never Set"
        }
    } else {
        "Never Set"
    }

    # Format password expiration date
    $passwordExpiration = if ($user.PasswordExpires) {
        try {
            [System.DateTime]::Parse($user.PasswordExpires).ToString("yyyy-MM-dd HH:mm:ss")
        } catch {
            "Never"
        }
    } else {
        "Never"
    }

    # Get account status
    $accountStatus = if ($user.Enabled) { "Enabled" } else { "Disabled" }

    # Get lockout status
    $lockedOut = if ($user.LockedOut) { $true } else { $false }

    # Get password expired status
    $passwordExpired = if ($user.PasswordExpired) { $true } else { $false }

    return @{
        FullName            = $user.CN
        Username            = $user.SamAccountName
        Email               = $user.EmailAddress
        PasswordLastReset   = $passwordLastReset
        PasswordExpirationDate = $passwordExpiration
        ClockID             = $user.EmployeeNumber
        Title               = $user.Description
        Department          = $user.Department
        LockedOut           = $lockedOut
        PasswordExpired     = $passwordExpired
        AccountStatus       = $accountStatus
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
        return "{}"
    }

    # Pad the username with leading zeros if it's numeric and less than 5 digits
    if ($Username -match '^\d{1,4}$') {
        $Username = $Username.PadLeft(5, '0')
    }

    try {
        Import-Module ActiveDirectory -ErrorAction Stop
    } catch {
        Write-Error "Failed to import ActiveDirectory module"
        return "{}"
    }

    try {
        $adUser = Get-ADUser -Filter "(SamAccountName -eq '$Username') -or (EmployeeNumber -eq '$Username') -or (CN -eq '$Username')" -Properties * -ErrorAction Stop

        if (-not $adUser) {
            return "{}"
        }

        $currentInfo = Write-UserBlock -user $adUser
        $cachedInfo = Load-UserFromFile -Username $currentInfo.Username

        # Always save current info to cache for future use
        Save-UserToFile -Username $currentInfo.Username -UserInfo $currentInfo

        return $currentInfo | ConvertTo-Json -Depth 3 -Compress
    } catch {
        Write-Error "Failed to get user information: $($_.Exception.Message)"
        return "{}"
    }
}

# Command-line Argument Support
if ($args.Count -gt 0) {
    Get-UserByUsername -Username $args[0]
}
