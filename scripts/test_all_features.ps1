$BASE = "http://13.234.21.145"
$pass = 0; $fail = 0; $results = @()

function Check($name, $ok, $detail) {
    $icon = if ($ok) { "PASS" } else { "FAIL" }
    $script:results += "[$icon] $name -- $detail"
    if ($ok) { $script:pass++ } else { $script:fail++ }
}

Write-Output "=== JobTruth Full Feature Test  ===`n"

# 1. Health
try {
    $r = Invoke-RestMethod "$BASE/health" -TimeoutSec 10
    Check "Health check" ($r.status -eq "ok") "status=$($r.status), served_by=$($r.served_by)"
} catch { Check "Health check" $false $_.Exception.Message }

# 2. Homepage
try {
    $r = Invoke-WebRequest "$BASE/" -TimeoutSec 10 -UseBasicParsing
    Check "Homepage (GET /)" ($r.StatusCode -eq 200) "HTTP $($r.StatusCode), $($r.Content.Length) bytes"
} catch { Check "Homepage (GET /)" $false $_.Exception.Message }

# 3. Stats
try {
    $r = Invoke-RestMethod "$BASE/stats" -TimeoutSec 10
    Check "Stats endpoint" ($null -ne $r.scams_detected) "scams_detected=$($r.scams_detected), reported=$($r.scams_reported)"
} catch { Check "Stats endpoint" $false $_.Exception.Message }

# 4. Register
$ts   = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$email = "testuser_$ts@example.com"
$body  = '{"email":"' + $email + '","password":"TestPass123!"}'
$token = $null
try {
    $r = Invoke-RestMethod "$BASE/auth/register" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 10
    $token = $r.access_token
    Check "Register user" ($null -ne $token) "email=$email"
} catch { Check "Register user" $false $_.Exception.Message }

# 5. Duplicate registration blocked
try {
    Invoke-RestMethod "$BASE/auth/register" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 10 | Out-Null
    Check "Duplicate register blocked" $false "Should have been 400"
} catch {
    Check "Duplicate register blocked" ($_.Exception.Response.StatusCode.value__ -eq 400) "HTTP $($_.Exception.Response.StatusCode.value__)"
}

# 6. Login
try {
    $r = Invoke-RestMethod "$BASE/auth/login" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 10
    Check "Login" ($null -ne $r.access_token) "token received"
} catch { Check "Login" $false $_.Exception.Message }

# 7. Wrong password
$wb = '{"email":"' + $email + '","password":"wrongpass"}'
try {
    Invoke-RestMethod "$BASE/auth/login" -Method POST -Body $wb -ContentType "application/json" -TimeoutSec 10 | Out-Null
    Check "Wrong password rejected" $false "Should be 401"
} catch {
    Check "Wrong password rejected" ($_.Exception.Response.StatusCode.value__ -eq 401) "HTTP $($_.Exception.Response.StatusCode.value__)"
}

# 8. Scam → High Risk
$scam = '{"text":"Urgent hiring! No interview needed. Pay Rs 2000 registration fee via UPI to hr@gmail.com. WhatsApp only. Earn Rs 5000 per day!"}'
try {
    $r = Invoke-RestMethod "$BASE/analyze" -Method POST -Body $scam -ContentType "application/json" -TimeoutSec 15
    Check "Scam text -> High Risk" ($r.label -eq "High Risk") "score=$($r.trust_score), label=$($r.label), flags=$($r.flags.Count)"
} catch { Check "Scam text -> High Risk" $false $_.Exception.Message }

# 9. Legit → Safe/Suspicious
$legit = '{"text":"Infosys is hiring engineers. Apply at infosys.com. Interview process included. Salary 4 LPA. Contact recruit@infosys.com"}'
try {
    $r = Invoke-RestMethod "$BASE/analyze" -Method POST -Body $legit -ContentType "application/json" -TimeoutSec 15
    Check "Legit text -> not High Risk" ($r.label -ne "High Risk") "score=$($r.trust_score), label=$($r.label)"
} catch { Check "Legit text -> not High Risk" $false $_.Exception.Message }

# 10. PII redaction present
$pii = '{"text":"Call John at 9876543210 or john@company.com, Aadhaar 1234 5678 9012"}'
try {
    $r = Invoke-RestMethod "$BASE/analyze" -Method POST -Body $pii -ContentType "application/json" -TimeoutSec 15
    Check "PII redacted_preview present" ($null -ne $r.redacted_preview) "preview length=$($r.redacted_preview.Length)"
} catch { Check "PII redaction" $false $_.Exception.Message }

# 11. Empty text validation
try {
    Invoke-RestMethod "$BASE/analyze" -Method POST -Body '{"text":""}' -ContentType "application/json" -TimeoutSec 10 | Out-Null
    Check "Empty text rejected (422)" $false "Should be 422"
} catch {
    Check "Empty text rejected (422)" ($_.Exception.Response.StatusCode.value__ -eq 422) "HTTP $($_.Exception.Response.StatusCode.value__)"
}

# 12. Headers all-pass
$gh = '{"raw_headers":"Authentication-Results: mx.google.com; spf=pass smtp.mailfrom=infosys.com; dkim=pass header.d=infosys.com; dmarc=pass"}'
try {
    $r = Invoke-RestMethod "$BASE/headers" -Method POST -Body $gh -ContentType "application/json" -TimeoutSec 10
    Check "Headers all pass -> Authenticated" ($r.verdict -eq "Authenticated") "spf=$($r.results.spf) dkim=$($r.results.dkim) dmarc=$($r.results.dmarc)"
} catch { Check "Headers all pass" $false $_.Exception.Message }

# 13. Headers fail
$bh = '{"raw_headers":"Authentication-Results: mx.google.com; spf=fail; dkim=none; dmarc=fail"}'
try {
    $r = Invoke-RestMethod "$BASE/headers" -Method POST -Body $bh -ContentType "application/json" -TimeoutSec 10
    Check "Headers fail -> Failed checks" ($r.verdict -eq "Failed checks") "verdict=$($r.verdict), flags=$($r.flags.Count)"
} catch { Check "Headers fail" $false $_.Exception.Message }

# 14. Known company verified
try {
    $r = Invoke-RestMethod "$BASE/company/verify?name=Infosys" -TimeoutSec 15
    Check "Known company (Infosys) is_real=1" ($r.is_real -eq 1) "is_real=$($r.is_real)"
} catch { Check "Known company" $false $_.Exception.Message }

# 15. Lookalike detected
try {
    $r = Invoke-RestMethod "$BASE/company/verify?name=Infosys+Careers+Pvt+Ltd" -TimeoutSec 15
    Check "Lookalike company detected" ($r.is_real -eq 0) "is_real=$($r.is_real), lookalike=$($r.lookalike)"
} catch { Check "Lookalike" $false $_.Exception.Message }

# 16. Fake company not verified
try {
    $r = Invoke-RestMethod "$BASE/company/verify?name=XyzFakeScam999" -TimeoutSec 20
    Check "Fake company -> not verified" ($r.is_real -eq 0) "is_real=$($r.is_real)"
} catch { Check "Fake company" $false $_.Exception.Message }

# 17. Upload PDF (magic bytes %PDF)
$pdfMagic = [byte[]]@(0x25,0x50,0x44,0x46,0x2d,0x31,0x2e,0x34,0x0a) + ([byte[]]::new(200))
$pdfKey = $null
try {
    $boundary = "Boundary1234567890"
    $nl = [byte[]]@(13,10)
    $headStr = "--$boundary`r`nContent-Disposition: form-data; name=`"file`"; filename=`"test.pdf`"`r`nContent-Type: application/pdf`r`n`r`n"
    $tailStr = "`r`n--$boundary--`r`n"
    $allBytes = [System.Text.Encoding]::ASCII.GetBytes($headStr) + $pdfMagic + [System.Text.Encoding]::ASCII.GetBytes($tailStr)
    $r = Invoke-RestMethod "$BASE/upload" -Method POST -Body $allBytes -ContentType "multipart/form-data; boundary=$boundary" -TimeoutSec 20
    $pdfKey = $r.key
    Check "Upload PDF (encrypted + integrity)" ($r.encryption -eq "AES256" -and $r.integrity_verified) "key=$($r.key), enc=$($r.encryption), ok=$($r.integrity_verified)"
} catch { Check "Upload PDF" $false $_.Exception.Message }

# 18. List objects
try {
    $r = Invoke-RestMethod "$BASE/objects" -TimeoutSec 10
    Check "List S3 objects" ($r -is [array]) "count=$($r.Count)"
} catch { Check "List S3 objects" $false $_.Exception.Message }

# 19. List versions
try {
    $r = Invoke-RestMethod "$BASE/versions" -TimeoutSec 10
    Check "List S3 versions" ($r -is [array]) "count=$($r.Count)"
} catch { Check "List S3 versions" $false $_.Exception.Message }

# 20. Delete uploaded object
if ($pdfKey) {
    try {
        $r = Invoke-RestMethod "$BASE/objects/$pdfKey" -Method DELETE -TimeoutSec 10
        Check "Delete S3 object (versioned)" ($null -ne $r.deleted) "deleted=$($r.deleted)"
    } catch { Check "Delete S3 object" $false $_.Exception.Message }
} else {
    Check "Delete S3 object" $false "Skipped (upload failed)"
}

# 21. Reject non-PDF
try {
    $fakeBytes = [System.Text.Encoding]::UTF8.GetBytes("this is not a real file at all")
    $boundary = "Boundary9999"
    $headStr = "--$boundary`r`nContent-Disposition: form-data; name=`"file`"; filename=`"fake.txt`"`r`nContent-Type: text/plain`r`n`r`n"
    $tailStr = "`r`n--$boundary--`r`n"
    $allBytes = [System.Text.Encoding]::ASCII.GetBytes($headStr) + $fakeBytes + [System.Text.Encoding]::ASCII.GetBytes($tailStr)
    Invoke-RestMethod "$BASE/upload" -Method POST -Body $allBytes -ContentType "multipart/form-data; boundary=$boundary" -TimeoutSec 10 | Out-Null
    Check "Reject non-PDF upload" $false "Should be 400"
} catch {
    Check "Reject non-PDF upload" ($_.Exception.Response.StatusCode.value__ -eq 400) "HTTP $($_.Exception.Response.StatusCode.value__)"
}

# 22. Path traversal blocked
try {
    Invoke-RestMethod "$BASE/objects/../../../etc/passwd" -Method DELETE -TimeoutSec 10 | Out-Null
    Check "Path traversal blocked" $false "Should be 400/404"
} catch {
    $c = $_.Exception.Response.StatusCode.value__
    Check "Path traversal blocked" ($c -in 400,404,422) "HTTP $c"
}

# ── Summary ──────────────────────────────────────────────────────────────────
Write-Output ""
Write-Output "======================================="
Write-Output " RESULTS"
Write-Output "======================================="
foreach ($line in $results) { Write-Output $line }
Write-Output ""
Write-Output "PASSED: $pass   FAILED: $fail   TOTAL: $($pass+$fail)"
Write-Output "======================================="
