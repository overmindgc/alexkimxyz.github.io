#!/bin/bash
echo "Unstaged changes:"
git st -s
read -n1 -p "Commit changes and deploy to master? [y,n]" doit 
case $doit in  
  y|Y) 
pelican content/ -s publishconf.py
git add .
git ci -m "update"
git push
ghp-import output -b master
git push origin master
;; 
  n|N) printf "\n Cancelling\n" 
;; 
  *) printf "\n Unrecognized input\n" ;; 
esac