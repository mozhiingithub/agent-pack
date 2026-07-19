查证完毕，清理干净临时仓库后汇总。以下问题我都没动，全部留给脚本维护方。                                                                                                                                                    
                                                                                                                                                                                                                               
   已修复（需维护方回填上游模板）                                                                                                                                                                                              
                                                                                                                                                                                                                               
   1. 分支名含 / 出包必败——export_package.sh:41 状态文件路径未转义，你已在本分支 33d32c5 修复（SAFE_BRANCH）。注意该 commit 改的是脚本固定区，按规范必须同步更新 agent-pack 上游模板，否则下次从模板再生的脚本会带病。         
                                                                                                                                                                                                                               
   新发现问题（本次复盘实证，均未修）                                                                                                                                                                                          
                                                                                                                                                                                                                               
   2. 保护路径硬阻断可被非 ASCII 文件名绕过（已实证）：export_package.sh:59 用裸 git diff --name-only | grep -q "^deploy-intranet/"，git 默认 core.quotePath=true 会把 deploy-intranet/中文.txt 输出成带引号的转义形式         
      "deploy-intranet/\344\270\255..."，^ 锚点匹配失败，阻断失效。同文件第 56 行倒是用了 -c core.quotePath=false，第 59、83 行没用——不一致。连带后果：第 83 行生成的 files.txt 里非 ASCII 路径也是转义形态，内网 import.sh:112
       按它校验 blob 必失败（包能出、导入必崩）。建议统一加 -c core.quotePath=false，或直接拒收路径含引号/转义的变更。                                                                                                         
   3. files.txt 实际按 blob 排序，不是规范要求的按 path：export_package.sh:83 是 LC_ALL=C sort -k2（第 2 字段是 blob）。本次 4 个文件恰好 blob 序与 path 序一致没暴露，规范写的是"按 path 排序"，应改 -t$'\t' -k3,3。确定性不受
      影响，属低危 spec 偏差。                                                                                                                                                                                                 
   4. export_package.sh:30 的 git ls-remote 是裸网络操作：不走 safe-git.sh，无重试、不读 .sync-state/proxy，网络抖动时前置校验会误报"分支 tip 未推送或与远端不一致"（本次重跑我就先撞到这个报错，虽然当时根因是修复 commit 未推
      送）。import.sh 有内置 net() 重试，出包侧是短板。                                                                                                                                                                        
   5. configImpact 误报：spec 模板强制"无则写'无'"，export_package.sh:93 把任何非空小节当部署影响，于是包里多了个只含"无"字的 configImpact.txt，还提示内网追加 [config] commit。脚本应把"无"/空白视为无影响，或模板允许留空——两
      者得对齐一个。                                                                                                                                                                                                           
                                                                                                                                                                                                                               
   内网实测前请转达执行人（import.sh 相关）                                                                                                                                                                                    
                                                                                                                                                                                                                               
   6. git am 需要提交者身份：import.sh:104 用 git am 应用 patch，内网机器若没配 user.name/user.email 会在这一步报 "Committer identity unknown" 然后还原退出。执行前先 git config --global user.name/user.email，或维护方在脚本 
      里加预检。                                                                                                                                                                                                               
   7. import.sh:19 的 REPO="$HOME/repos/project" 是占位路径，需按内网实际仓库路径改（可变区，允许改）。                                                                                                                        
                                                                                                                                                                                                                               
   另有一个运维备注：修复前的失败残留 outbox/sync-feat/ 不会被修复后的脚本自动清掉（转义后路径变了），我已手工删除。                                                                                                           
                                                                                                                                                                                                                               
   以上 2、3、4、5 建议原样转给 export/import 脚本维护方，尤其第 2 条是安全相关的硬阻断失效。                                                                                                                                  
 
 ● Ran a command                                                                   