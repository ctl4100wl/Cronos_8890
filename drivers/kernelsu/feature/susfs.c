// SPDX-License-Identifier: GPL-2.0
/* SUSFS v1.5.5 control ABI, adapted to KernelSU Next 3.4.0 / Cronos 3.18. */
#include <linux/cred.h>
#include <linux/errno.h>
#include <linux/namei.h>
#include <linux/mutex.h>
#include <linux/susfs.h>
#include <linux/uaccess.h>
#include "selinux/selinux.h"

bool susfs_is_current_ksu_domain(void)
{
	return is_ksu_domain();
}

bool susfs_is_current_zygote_domain(void)
{
	return is_zygote(current_cred());
}

static DEFINE_MUTEX(susfs_control_mutex);

extern void susfs_run_try_umount_for_current_mnt_ns(void);

int ksu_susfs_prctl(int option, unsigned long cmd, unsigned long arg,
		    unsigned long unused, unsigned long result)
{
	void __user *data = (void __user *)arg;
	int error = -EOPNOTSUPP;
	u64 features = 0;

	/* Do not intercept ordinary prctl or another KernelSU command. */
	if ((unsigned int)option != 0xDEADBEEF ||
	    !((cmd >= CMD_SUSFS_ADD_SUS_PATH && cmd <= CMD_SUSFS_IS_SUS_SU_READY) ||
	      cmd == CMD_SUSFS_SUS_SU))
		return -ENOSYS;
	/* A root UID alone must not expose the control path to another domain. */
	if (current_uid().val != 0 || !is_ksu_domain())
		return -EPERM;
	if (!access_ok(VERIFY_WRITE, (void __user *)result, sizeof(error)))
		return -EFAULT;

	mutex_lock(&susfs_control_mutex);
	switch (cmd) {
#ifdef CONFIG_KSU_SUSFS_SUS_PATH
	case CMD_SUSFS_ADD_SUS_PATH:
		error = susfs_add_sus_path(data);
		break;
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
	case CMD_SUSFS_ADD_SUS_MOUNT:
		error = susfs_add_sus_mount(data);
		break;
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT
	case CMD_SUSFS_ADD_SUS_KSTAT:
		error = susfs_add_sus_kstat(data);
		break;
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT
	case CMD_SUSFS_ADD_SUS_KSTAT_STATICALLY:
		error = susfs_add_sus_kstat(data);
		break;
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT
	case CMD_SUSFS_UPDATE_SUS_KSTAT:
		error = susfs_update_sus_kstat(data);
		break;
#endif
#ifdef CONFIG_KSU_SUSFS_TRY_UMOUNT
	case CMD_SUSFS_ADD_TRY_UMOUNT:
		error = susfs_add_try_umount(data);
		break;
#endif
#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME
	case CMD_SUSFS_SET_UNAME:
		error = susfs_set_uname(data);
		break;
#endif
#ifdef CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG
	case CMD_SUSFS_SET_CMDLINE_OR_BOOTCONFIG:
		error = susfs_set_cmdline_or_bootconfig(data);
		break;
#endif
#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT
	case CMD_SUSFS_ADD_OPEN_REDIRECT:
		error = susfs_add_open_redirect(data);
		break;
#endif
#ifdef CONFIG_KSU_SUSFS_ENABLE_LOG
	case CMD_SUSFS_ENABLE_LOG:
		susfs_set_log(arg != 0);
		error = 0;
		break;
#endif
#ifdef CONFIG_KSU_SUSFS_TRY_UMOUNT
	case CMD_SUSFS_RUN_UMOUNT_FOR_CURRENT_MNT_NS:
		susfs_run_try_umount_for_current_mnt_ns();
		error = 0;
		break;
#endif
	case CMD_SUSFS_SHOW_VERSION:
		error = copy_to_user(data, SUSFS_VERSION, sizeof(SUSFS_VERSION)) ? -EFAULT : 0;
		break;
	case CMD_SUSFS_SHOW_VARIANT:
		error = copy_to_user(data, SUSFS_VARIANT, sizeof(SUSFS_VARIANT)) ? -EFAULT : 0;
		break;
	case CMD_SUSFS_SHOW_ENABLED_FEATURES:
#ifdef CONFIG_KSU_SUSFS_SUS_PATH
		features |= 1ULL << 0;
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
		features |= 1ULL << 1;
#endif
#ifdef CONFIG_KSU_SUSFS_AUTO_ADD_SUS_KSU_DEFAULT_MOUNT
		features |= 1ULL << 2;
#endif
#ifdef CONFIG_KSU_SUSFS_AUTO_ADD_SUS_BIND_MOUNT
		features |= 1ULL << 3;
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT
		features |= 1ULL << 4;
#endif
#ifdef CONFIG_KSU_SUSFS_TRY_UMOUNT
		features |= 1ULL << 6;
#endif
#ifdef CONFIG_KSU_SUSFS_AUTO_ADD_TRY_UMOUNT_FOR_BIND_MOUNT
		features |= 1ULL << 7;
#endif
#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME
		features |= 1ULL << 8;
#endif
#ifdef CONFIG_KSU_SUSFS_ENABLE_LOG
		features |= 1ULL << 9;
#endif
#ifdef CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS
		features |= 1ULL << 10;
#endif
#ifdef CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG
		features |= 1ULL << 11;
#endif
#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT
		features |= 1ULL << 12;
#endif
#ifdef CONFIG_KSU_SUSFS_HAS_MAGIC_MOUNT
		features |= 1ULL << 14;
#endif
		error = copy_to_user(data, &features, sizeof(features)) ? -EFAULT : 0;
		break;
	default:
		break;
	}
	mutex_unlock(&susfs_control_mutex);
	return copy_to_user((void __user *)result, &error, sizeof(error)) ? -EFAULT : 0;
}
