$a = dir C:\files
$a | select-object @{name="date";expression={$_.creationtime.ToString("MM/dd/yyyy")}},@{name="time";expression={$_.creationtime.ToString("HH:mm")}},@{name="size";expression={$_.length}},@{name="name";expression={$_.name}} | export-csv ("DirList_"+[System.DateTime]::Now.ToString("MM_dd_yyyy") + ".csv")
$x = get-content $("DirList_"+[System.DateTime]::Now.ToString("MM_dd_yyyy") + ".csv")
$x[1..$x.count] -replace '\"','' | set-content $("C:\Summary\DirList_"+[System.DateTime]::Now.ToString("MM_dd_yyyy") + ".csv")

