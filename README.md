# OpenWRT-CI
云编译个人自用的OpenWRT固件

immortalwrt源码仓库：
https://github.com/immortalwrt/immortalwrt.git

VIKINGYFY的QCA immortalwrt源码仓库:
https://github.com/VIKINGYFY/immortalwrt.git

LiBwrt源码仓库：
https://github.com/LiBwrt/openwrt-6.x.git

# 固件简要说明：

固件每三天早上4点自动编译。

固件信息里的时间为编译开始的时间，方便核对上游源码提交时间。

固件修改了内核分区大小到12M，需要特定的Uboot/分区表才能使用

# 目录简要说明：

workflows——自定义CI配置

Scripts——自定义脚本

Config——自定义配置
