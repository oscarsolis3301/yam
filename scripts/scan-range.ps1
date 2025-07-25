param(
    [Parameter(Mandatory)]
    [string] $Subnet,           # e.g. "192.168.1"
    [int]    $TimeoutMs   = 500,# per-ping timeout in ms
    [int]    $ThrottleLimit = 50# max concurrent threads
)

1..255 | ForEach-Object -Parallel {
    param($base, $tm)

    $ip = "$base.$_"

    # quick ping
    $online = Test-Connection -ComputerName $ip `
                              -Count 1 `
                              -Quiet `
                              -TimeoutMilliseconds $tm

    # direct .NET DNS lookup
    try {
        $resolvedName = [System.Net.Dns]::GetHostEntry($ip).HostName
    } catch {
        $resolvedName = ''
    }

    [PSCustomObject]@{
        ip       = $ip
        hostname = $resolvedName
        online   = $online
    }
} -ArgumentList $Subnet, $TimeoutMs `
  -ThrottleLimit $ThrottleLimit `
  | ConvertTo-Json -Depth 2
