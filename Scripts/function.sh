#!/bin/bash

function cat_kernel_config() {
  if [ -f $1 ]; then
    cat >> $1 <<EOF
CONFIG_BPF=y
CONFIG_BPF_SYSCALL=y
CONFIG_BPF_JIT=y
CONFIG_CGROUPS=y
CONFIG_KPROBES=y
CONFIG_NET_INGRESS=y
CONFIG_NET_EGRESS=y
CONFIG_NET_SCH_INGRESS=m
CONFIG_NET_CLS_BPF=m
CONFIG_NET_CLS_ACT=y
CONFIG_BPF_STREAM_PARSER=y
CONFIG_DEBUG_INFO=y
# CONFIG_DEBUG_INFO_REDUCED is not set
CONFIG_DEBUG_INFO_BTF=y
CONFIG_KPROBE_EVENTS=y
CONFIG_BPF_EVENTS=y

CONFIG_SCHED_CLASS_EXT=y
CONFIG_PROBE_EVENTS_BTF_ARGS=y
CONFIG_IMX_SCMI_MISC_DRV=y
CONFIG_ARM64_CONTPTE=y
CONFIG_TRANSPARENT_HUGEPAGE=y
CONFIG_TRANSPARENT_HUGEPAGE_ALWAYS=y
# CONFIG_TRANSPARENT_HUGEPAGE_MADVISE is not set
# CONFIG_TRANSPARENT_HUGEPAGE_NEVER is not set
EOF
    echo "cat_kernel_config to $1 done"
  fi
}

function cat_ebpf_config() {

#ebpf相关
  cat >> $1 <<EOF
#eBPF
CONFIG_DEVEL=y
CONFIG_KERNEL_DEBUG_INFO=y
CONFIG_KERNEL_DEBUG_INFO_REDUCED=n
CONFIG_KERNEL_DEBUG_INFO_BTF=y
CONFIG_KERNEL_CGROUPS=y
CONFIG_KERNEL_CGROUP_BPF=y
CONFIG_KERNEL_BPF_EVENTS=y
CONFIG_BPF_TOOLCHAIN_HOST=y
CONFIG_KERNEL_XDP_SOCKETS=y
CONFIG_PACKAGE_kmod-xdp-sockets-diag=y
EOF
}

function set_kernel_size() {
  #修改jdc ax1800 pro 的内核大小为12M
  image_file='./target/linux/qualcommax/image/ipq60xx.mk'
  sed -i "/^define Device\/jdcloud_re-ss-01/,/^endef/ { /KERNEL_SIZE := 6144k/s//KERNEL_SIZE := 12288k/ }" $image_file
  sed -i "/^define Device\/jdcloud_re-cs-02/,/^endef/ { /KERNEL_SIZE := 6144k/s//KERNEL_SIZE := 12288k/ }" $image_file
  sed -i "/^define Device\/jdcloud_re-cs-07/,/^endef/ { /KERNEL_SIZE := 6144k/s//KERNEL_SIZE := 12288k/ }" $image_file
  sed -i "/^define Device\/redmi_ax5-jdcloud/,/^endef/ { /KERNEL_SIZE := 6144k/s//KERNEL_SIZE := 12288k/ }" $image_file
}


function generate_config() {
  config_file=".config"
  #如配置文件已存在
  cat $GITHUB_WORKSPACE/Config/${WRT_CONFIG}.txt $GITHUB_WORKSPACE/Config/GENERAL.txt  > $config_file
  local target=$(echo $WRT_ARCH | cut -d'_' -f2)
  #增加ebpf
  cat_ebpf_config $config_file
  set_kernel_size

}






