const { exec } = require('child_process')

function setOutput(key, value) {
    console.log(`Set ${key}=${value}`)
    console.log(`::set-output name=${key}::${value}`)
}

function error(message) {
    console.log(`::error::${message}`)
}

function debug(message) {
    console.log(`::debug::${message}`)
}

const BRANCH_REF_PREFIX = "refs/heads/"

try {
    console.log(`Calculating NSG version for ${process.env.GITHUB_REF} (${process.env.GITHUB_SHA})`)
    debug(`git commit ${process.env.GITHUB_SHA}`)
    debug(`git ref ${process.env.GITHUB_REF}`)

    const git_commit = process.env.GITHUB_SHA
    let git_branch = ""
    if ( process.env.GITHUB_REF.startsWith(BRANCH_REF_PREFIX) ) {
        git_branch = process.env.GITHUB_REF.slice(BRANCH_REF_PREFIX.length)
    }

    const git_branch_safe = git_branch.replace("/", "-")
    const is_release_branch = ["master", "main", "release"].indexOf(git_branch) !== -1 || git_branch.startsWith("release/")
    const is_development_branch = ["develop", "development"].indexOf(git_branch) !== -1
    const is_feature_branch_or_pr = !is_release_branch && !is_development_branch

    setOutput("is_release_branch", is_release_branch.toString())
    setOutput("is_development_branch", is_development_branch.toString())
    setOutput("is_feature_branch_or_pr", is_feature_branch_or_pr.toString())

    setOutput("git_branch", git_branch)
    setOutput("git_branch_safe", git_branch_safe)

    // actions@checkout performs a shallow checkout. Need to unshallow for full tags access.
    let cmd = "git fetch --prune --unshallow && git describe --tags --abbrev=1 --long"
    debug(`Executing: ${cmd}`)

    exec(cmd, (err, output, stderr) => {
        if (err) {
            error(`Unable to find an earlier tag.\n${stderr}`)
            return process.exit(1)
        }
        const git_describe = output.trim()
        debug(`git describe output: ${git_describe}`)

        const parts = git_describe.split("-")
        // Remove "v" prefix if it exits
        const git_tag = parts[0].replace(/^v/, '')
        const git_commits_since_tag = parts[1]
        // Remove "g" prefix
        const git_describe_object_id = parts[2].slice(1)

        let long_version = `${git_tag}`
        if ( is_feature_branch_or_pr ) {
            long_version += `.${git_commits_since_tag}`
        }

        setOutput("git_tag", git_tag)
        setOutput("version", git_tag)
        setOutput("git_commit", git_commit)
        setOutput("git_describe_object_id", git_describe_object_id)
        setOutput("git_commits_since_tag", git_commits_since_tag)
        setOutput("git_describe", git_describe)
        setOutput("long_version", long_version)

        console.log(`NSG Version is "${long_version}"`)
    })
} catch (error) {
    process.exitCode = 1
    error(error.message);
}