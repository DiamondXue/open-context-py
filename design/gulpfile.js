var gulp = require('gulp');
var rename = require('gulp-rename');
var concat = require('gulp-concat');
var browserSync = require('browser-sync');
var reload = browserSync.reload;
var pkg = require('./package.json');
var autoprefixer = require('gulp-autoprefixer');
var changed = require('gulp-changed');
var uglify = require('gulp-uglify');
var w3cjs = require('gulp-w3cjs');
var sass = require('gulp-sass');

var scssFiles = "src/sass/**/*.scss";
var cssCompileDir = "www/css";

// Carry over misc files,
// but only if they changed.
gulp.task('misc-files', function () {
  gulp.src(['src/CNAME', 'src/*.js', 'src/*.pdf', 'src/robots.txt', 'src/images/favicons/*'])
    .pipe(changed("./www"))
    .pipe(gulp.dest("./www"));
});

// HTML Validator
gulp.task('validate', function () {
  gulp.src('www/*.html')
    .pipe(w3cjs());
});

// Sass stylesheets
var sassConfig = {
  errLogToConsole: true,
  includePaths: ["bower_components"],
  outputStyle: "compressed"
}

gulp.task('sass', function () {
  return gulp.src(scssFiles)
    .pipe(sass(sassConfig))
    .pipe(autoprefixer("last 4 versions", "> 1%"))
    .pipe(gulp.dest(cssCompileDir))
    .pipe(reload({
      stream: true
    }))
});

// Browser-sync
var browserSyncConfig = {
  reloadDelay: 2000,
  notify: false,
  server: {
    baseDir: "./www",
  }
}

// Default task
gulp.task('default', function () {
  gulp.watch(scssFiles, ['sass']);
  browserSync(browserSyncConfig);
});