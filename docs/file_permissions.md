# Handling file permissions
dfu aims to capture and preserve detailed file permissions for each file and folder. This includes the mode bits (read, write, execute), setuid/setgid, and the user/group as a symbolic name where possible

That way, when applying a patch, this metadata is preserved. However, git does not save or restore metadata in this manner. Git only tracks whether a file is executable (+x). When you git clone a repository, it uses the current user as the owner (subject to e.g. any usmasks). When you git commit a file, it only tracks whether it's marked as executable for the current user.

Root permissions cause additional headaches when trying to create git patches. If you have a file that is owned by root, with mode o600, then `git add` will fail because git doesn't have permission to read the file. Running `sudo git` is a bad solution for many reasons.

# Dfu implementation 
When dfu loads a btrfs snapshot, it will first enumerate through the entire snapshot as the root user. Dfu will generate a acl.txt file. Each line contains the following space separated fields
`path mode user:group`
For example:
```
/etc/ 0755 root:root
/etc/mkinitcpio.conf 0644 root:root
/tmp/file.iso 0644 nil:nil {"trusted.md5sum":"abc123"}
```

Next, all the files and folders are copied over with permissive settings to ensure that git can properly access them. All files are owned by the current user with 0o755 permissions. Since we are doing our own thing, we are going to completely ignore the executable flag within git (hence the 644 for files)

This will allow git to see and edit any file in the playground. Now we can do all of the normal operations, such as `git add`, or `git merge` to apply the changes to the playground.

Once this is complete, dfu will use the acl.txt file to set the permissions of the file when copying the file over to the filesystem. Any change to permissions of the file in the playground itself are ignored.

# Security implications of this approach
Files are usually protected to read-only-by-root to ensure things like passwords and such are not accessed by a non-privileged user. Dfu pokes holes in this approach in a few ways that are worth calling out. When creating the playground, these files are accessible by any process running as the current user. Theoretically, if a malicious user application is running as the current user, AND the user runs `dfu diff` AND the snapshot contains something sensitive, this could be potentially exfiltrated by the user.

Once the snapshot is created, the `.pack` file is readable by the current user, and will contain the same information (e.g. any potentially sensitive information in the files saved)

This is considered **by design**. If you are worried about malicious programs active on the machine, you have bigger problems than running `dfu diff`.

A future update to dfu may encrypt the .pack files (but that just moves the problem to a mechanism to secure the keychain for the encryption key). In the mean time, if you want to prevent usermode applications from reading these files, you'll need to implement a solution yourself.
