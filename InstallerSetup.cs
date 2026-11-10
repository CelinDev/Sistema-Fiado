using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Win32;

[assembly: AssemblyTitle("Instalador - Fiado Manager")]
[assembly: AssemblyDescription("Instalador Oficial do Fiado Manager")]
[assembly: AssemblyCompany("Fiado Manager Software")]
[assembly: AssemblyProduct("Fiado Manager")]
[assembly: AssemblyVersion("1.0.0.0")]
[assembly: AssemblyFileVersion("1.0.0.0")]

namespace FiadoManagerInstaller
{
    public class InstallerForm : Form
    {
        private TextBox txtInstallPath;
        private CheckBox chkDesktopShortcut;
        private CheckBox chkStartMenuShortcut;
        private CheckBox chkLaunchAfter;
        private Button btnBrowse;
        private Button btnInstall;
        private Button btnCancel;
        private ProgressBar progressBar;
        private Label lblStatus;
        private bool isInstalled = false;
        private string installedExePath = "";

        public InstallerForm()
        {
            InitializeComponents();
        }

        private void InitializeComponents()
        {
            this.Text = "Instalador - Fiado Manager v1.0.0";
            this.Size = new Size(540, 390);
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox = false;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.BackColor = Color.FromArgb(248, 250, 252);
            this.Font = new Font("Segoe UI", 9.5F, FontStyle.Regular);

            // Header Panel
            Panel headerPanel = new Panel();
            headerPanel.Dock = DockStyle.Top;
            headerPanel.Height = 75;
            headerPanel.BackColor = Color.FromArgb(30, 41, 59);

            Label lblTitle = new Label();
            lblTitle.Text = "Fiado Manager";
            lblTitle.Font = new Font("Segoe UI", 16F, FontStyle.Bold);
            lblTitle.ForeColor = Color.White;
            lblTitle.Location = new Point(22, 12);
            lblTitle.AutoSize = true;

            Label lblSubtitle = new Label();
            lblSubtitle.Text = "Sistema de Gestão de Crédito e Clientes - Versão 1.0.0";
            lblSubtitle.Font = new Font("Segoe UI", 9.5F, FontStyle.Regular);
            lblSubtitle.ForeColor = Color.FromArgb(148, 163, 184);
            lblSubtitle.Location = new Point(24, 44);
            lblSubtitle.AutoSize = true;

            headerPanel.Controls.Add(lblTitle);
            headerPanel.Controls.Add(lblSubtitle);
            this.Controls.Add(headerPanel);

            // Directory Label
            Label lblDir = new Label();
            lblDir.Text = "Pasta de Instalação:";
            lblDir.Font = new Font("Segoe UI", 9.5F, FontStyle.Bold);
            lblDir.ForeColor = Color.FromArgb(51, 65, 85);
            lblDir.Location = new Point(24, 95);
            lblDir.AutoSize = true;
            this.Controls.Add(lblDir);

            string defaultPath = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "Programs",
                "FiadoManager"
            );

            txtInstallPath = new TextBox();
            txtInstallPath.Text = defaultPath;
            txtInstallPath.Location = new Point(24, 120);
            txtInstallPath.Size = new Size(375, 25);
            this.Controls.Add(txtInstallPath);

            btnBrowse = new Button();
            btnBrowse.Text = "Procurar...";
            btnBrowse.Location = new Point(408, 118);
            btnBrowse.Size = new Size(92, 27);
            btnBrowse.FlatStyle = FlatStyle.System;
            btnBrowse.Click += BtnBrowse_Click;
            this.Controls.Add(btnBrowse);

            // Checkboxes
            chkDesktopShortcut = new CheckBox();
            chkDesktopShortcut.Text = "Criar atalho na Área de Trabalho";
            chkDesktopShortcut.Checked = true;
            chkDesktopShortcut.Location = new Point(24, 162);
            chkDesktopShortcut.AutoSize = true;
            this.Controls.Add(chkDesktopShortcut);

            chkStartMenuShortcut = new CheckBox();
            chkStartMenuShortcut.Text = "Criar atalho no Menu Iniciar";
            chkStartMenuShortcut.Checked = true;
            chkStartMenuShortcut.Location = new Point(24, 190);
            chkStartMenuShortcut.AutoSize = true;
            this.Controls.Add(chkStartMenuShortcut);

            chkLaunchAfter = new CheckBox();
            chkLaunchAfter.Text = "Iniciar o Fiado Manager ao concluir a instalação";
            chkLaunchAfter.Checked = true;
            chkLaunchAfter.Location = new Point(24, 218);
            chkLaunchAfter.AutoSize = true;
            this.Controls.Add(chkLaunchAfter);

            // Status and Progress
            lblStatus = new Label();
            lblStatus.Text = "Pronto para instalar.";
            lblStatus.ForeColor = Color.FromArgb(71, 85, 105);
            lblStatus.Location = new Point(24, 255);
            lblStatus.Size = new Size(476, 20);
            this.Controls.Add(lblStatus);

            progressBar = new ProgressBar();
            progressBar.Location = new Point(24, 278);
            progressBar.Size = new Size(476, 18);
            progressBar.Style = ProgressBarStyle.Continuous;
            this.Controls.Add(progressBar);

            // Bottom Buttons
            btnInstall = new Button();
            btnInstall.Text = "Instalar Agora";
            btnInstall.Font = new Font("Segoe UI", 9.5F, FontStyle.Bold);
            btnInstall.BackColor = Color.FromArgb(37, 99, 235);
            btnInstall.ForeColor = Color.White;
            btnInstall.FlatStyle = FlatStyle.Flat;
            btnInstall.FlatAppearance.BorderSize = 0;
            btnInstall.Location = new Point(280, 310);
            btnInstall.Size = new Size(125, 32);
            btnInstall.Cursor = Cursors.Hand;
            btnInstall.Click += BtnInstall_Click;
            this.Controls.Add(btnInstall);

            btnCancel = new Button();
            btnCancel.Text = "Cancelar";
            btnCancel.Location = new Point(415, 310);
            btnCancel.Size = new Size(85, 32);
            btnCancel.FlatStyle = FlatStyle.System;
            btnCancel.Click += (s, e) => this.Close();
            this.Controls.Add(btnCancel);
        }

        private void BtnBrowse_Click(object sender, EventArgs e)
        {
            using (var dialog = new FolderBrowserDialog())
            {
                dialog.Description = "Selecione a pasta onde deseja instalar o Fiado Manager:";
                dialog.SelectedPath = txtInstallPath.Text;
                if (dialog.ShowDialog() == DialogResult.OK)
                {
                    string selected = dialog.SelectedPath;
                    if (!selected.EndsWith("FiadoManager", StringComparison.OrdinalIgnoreCase))
                    {
                        selected = Path.Combine(selected, "FiadoManager");
                    }
                    txtInstallPath.Text = selected;
                }
            }
        }

        private async void BtnInstall_Click(object sender, EventArgs e)
        {
            if (isInstalled)
            {
                if (chkLaunchAfter.Checked && File.Exists(installedExePath))
                {
                    ProcessStartInfo psi = new ProcessStartInfo(installedExePath);
                    psi.WorkingDirectory = Path.GetDirectoryName(installedExePath);
                    Process.Start(psi);
                }
                this.Close();
                return;
            }

            string targetDir = txtInstallPath.Text.Trim();
            if (string.IsNullOrEmpty(targetDir))
            {
                MessageBox.Show("Por favor, informe um caminho válido para a instalação.", "Aviso", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            btnInstall.Enabled = false;
            btnBrowse.Enabled = false;
            txtInstallPath.Enabled = false;
            chkDesktopShortcut.Enabled = false;
            chkStartMenuShortcut.Enabled = false;

            bool createDesktop = chkDesktopShortcut.Checked;
            bool createStartMenu = chkStartMenuShortcut.Checked;

            try
            {
                await Task.Run(() => RunInstallation(targetDir, createDesktop, createStartMenu));

                isInstalled = true;
                installedExePath = Path.Combine(targetDir, "FiadoManager.exe");

                lblStatus.Text = "Instalação concluída com sucesso!";
                lblStatus.ForeColor = Color.FromArgb(22, 163, 74);
                progressBar.Value = 100;

                btnInstall.Text = "Concluir";
                btnInstall.BackColor = Color.FromArgb(22, 163, 74);
                btnInstall.Enabled = true;
                btnCancel.Visible = false;

                MessageBox.Show(
                    "O Fiado Manager foi instalado com sucesso no seu computador!",
                    "Instalação Concluída",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Information
                );
            }
            catch (Exception ex)
            {
                lblStatus.Text = "Erro durante a instalação.";
                lblStatus.ForeColor = Color.FromArgb(220, 38, 38);
                MessageBox.Show(
                    "Ocorreu um erro durante a instalação:\n\n" + ex.Message,
                    "Erro na Instalação",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
                btnInstall.Enabled = true;
                btnBrowse.Enabled = true;
                txtInstallPath.Enabled = true;
                chkDesktopShortcut.Enabled = true;
                chkStartMenuShortcut.Enabled = true;
            }
        }

        private void UpdateProgress(string status, int value)
        {
            if (this.InvokeRequired)
            {
                this.Invoke(new Action(() => UpdateProgress(status, value)));
                return;
            }
            lblStatus.Text = status;
            progressBar.Value = Math.Min(100, Math.Max(0, value));
        }

        private void RunInstallation(string targetDir, bool createDesktop, bool createStartMenu)
        {
            UpdateProgress("Verificando processos em execução...", 5);
            foreach (var proc in Process.GetProcessesByName("FiadoManager"))
            {
                try
                {
                    proc.Kill();
                    proc.WaitForExit(3000);
                }
                catch { }
            }

            UpdateProgress("Preparando diretório de destino...", 10);
            if (!Directory.Exists(targetDir))
            {
                Directory.CreateDirectory(targetDir);
            }

            UpdateProgress("Extraindo arquivos do aplicativo...", 15);
            Assembly assembly = Assembly.GetExecutingAssembly();
            string resourceName = null;
            foreach (string name in assembly.GetManifestResourceNames())
            {
                if (name.EndsWith("payload.zip", StringComparison.OrdinalIgnoreCase))
                {
                    resourceName = name;
                    break;
                }
            }

            if (resourceName == null)
            {
                throw new Exception("Pacote de instalação interno (payload.zip) não encontrado no executável.");
            }

            using (Stream stream = assembly.GetManifestResourceStream(resourceName))
            using (ZipArchive archive = new ZipArchive(stream, ZipArchiveMode.Read))
            {
                int totalEntries = archive.Entries.Count;
                int current = 0;

                foreach (ZipArchiveEntry entry in archive.Entries)
                {
                    current++;
                    string fullPath = Path.Combine(targetDir, entry.FullName);
                    string directoryPath = Path.GetDirectoryName(fullPath);

                    if (!string.IsNullOrEmpty(directoryPath) && !Directory.Exists(directoryPath))
                    {
                        Directory.CreateDirectory(directoryPath);
                    }

                    if (!string.IsNullOrEmpty(entry.Name))
                    {
                        entry.ExtractToFile(fullPath, true);
                    }

                    if (current % 10 == 0 || current == totalEntries)
                    {
                        int pct = 15 + (int)((current / (double)totalEntries) * 70);
                        UpdateProgress(string.Format("Extraindo arquivos ({0}/{1})...", current, totalEntries), pct);
                    }
                }
            }

            string targetExe = Path.Combine(targetDir, "FiadoManager.exe");

            if (createStartMenu)
            {
                UpdateProgress("Criando atalho no Menu Iniciar...", 88);
                string startMenu = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                    @"Microsoft\Windows\Start Menu\Programs\Fiado Manager.lnk"
                );
                CreateShortcut(startMenu, targetExe, targetDir, "Fiado Manager - Gestão de Crédito e Clientes");
            }

            if (createDesktop)
            {
                UpdateProgress("Criando atalho na Área de Trabalho...", 92);
                string desktop = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),
                    "Fiado Manager.lnk"
                );
                CreateShortcut(desktop, targetExe, targetDir, "Fiado Manager - Gestão de Crédito e Clientes");
            }

            UpdateProgress("Configurando desinstalador e registro...", 96);
            CreateUninstaller(targetDir, targetExe);

            UpdateProgress("Finalizando...", 100);
        }

        private void CreateShortcut(string shortcutPath, string targetExe, string workingDir, string description)
        {
            Type shellType = Type.GetTypeFromProgID("WScript.Shell");
            dynamic shell = Activator.CreateInstance(shellType);
            dynamic shortcut = shell.CreateShortcut(shortcutPath);
            shortcut.TargetPath = targetExe;
            shortcut.WorkingDirectory = workingDir;
            shortcut.Description = description;
            shortcut.IconLocation = targetExe + ",0";
            shortcut.Save();
        }

        private void CreateUninstaller(string targetDir, string targetExe)
        {
            string uninstallBat = Path.Combine(targetDir, "uninstall.bat");
            string batContent = string.Join("\r\n", new string[] {
                "@echo off",
                "chcp 65001 >nul",
                "title Desinstalador - Fiado Manager",
                "echo ==========================================================",
                "echo        DESINSTALADOR - FIADO MANAGER",
                "echo ==========================================================",
                "echo.",
                "set /p CONFIRM=\"Deseja realmente remover o Fiado Manager do computador? (S/N): \"",
                "if /i not \"%CONFIRM%\"==\"S\" exit /b",
                "echo Fechando aplicacao se estiver em execucao...",
                "taskkill /f /im FiadoManager.exe 2>nul",
                "echo Removendo atalhos...",
                "del /q \"%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Fiado Manager.lnk\" 2>nul",
                "del /q \"%USERPROFILE%\\Desktop\\Fiado Manager.lnk\" 2>nul",
                "reg delete \"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\FiadoManager\" /f 2>nul",
                "echo Removendo arquivos do programa...",
                "cd /d \"%TEMP%\"",
                "rd /s /q \"" + targetDir + "\" 2>nul",
                "echo.",
                "echo Desinstalacao concluida com sucesso!",
                "echo Nota: Seus dados e banco de dados em '%APPDATA%\\FiadoManager' foram preservados.",
                "pause"
            });
            File.WriteAllText(uninstallBat, batContent);

            try
            {
                using (RegistryKey key = Registry.CurrentUser.CreateSubKey(@"Software\Microsoft\Windows\CurrentVersion\Uninstall\FiadoManager"))
                {
                    if (key != null)
                    {
                        key.SetValue("DisplayName", "Fiado Manager");
                        key.SetValue("DisplayVersion", "1.0.0");
                        key.SetValue("Publisher", "Fiado Manager Software");
                        key.SetValue("InstallLocation", targetDir);
                        key.SetValue("DisplayIcon", targetExe + ",0");
                        key.SetValue("UninstallString", "\"" + uninstallBat + "\"");
                        key.SetValue("NoModify", 1, RegistryValueKind.DWord);
                        key.SetValue("NoRepair", 1, RegistryValueKind.DWord);
                    }
                }
            }
            catch { }
        }

        [STAThread]
        public static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new InstallerForm());
        }
    }
}
